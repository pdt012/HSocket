# -*- coding: utf-8 -*-
from typing import Tuple, Optional, Union, List, Dict, Any
import socket
import os
from .message import Header, Message, MessageConfig


FTP_PORT = 1
FTP_PASV = 2


class SocketConfig:
    BUFFER_SIZE = 1024
    DEFAULT_DOWNLOAD_PATH = "downloads/"


class HSocketTcp(socket.socket):
    def __init__(self, family=socket.AF_INET, type_=socket.SOCK_STREAM, proto=-1, fileno=None):
        super().__init__(family, type_, proto, fileno)
    
    def accept(self) -> Tuple["HSocketTcp", Tuple[str, int]]:
        fd, addr = self._accept()
        sock = HSocketTcp(self.family, self.type, self.proto, fileno=fd)
        if self.gettimeout():
            sock.setblocking(True)
        return sock, addr

    def sendMsg(self, msg: "Message") -> bool:
        data = msg.to_bytes()
        self.sendall(data)
        return True

    def recvMsg(self) -> "Message":
        data = b""
        header = Header.from_bytes(self.recv(Header.HEADER_LENGTH))
        if header:
            size = header.length
            while len(data) < size:  # 未接收完
                recv_size = min(size - len(data), SocketConfig.BUFFER_SIZE)
                recv_data = self.recv(recv_size)
                data += recv_data
            if data:
                return Message.HeaderContent(header, data.decode(MessageConfig.ENCODING))
            else:
                return Message.HeaderContent(header, "")
        else:
            return Message()

    def sendFile(self, path: str, filename: str) -> bool:
        if not os.path.isfile(path):
            return False
        filesize = os.stat(path).st_size
        file_header_msg = Message.JsonMsg(1001, 0, {"filename": filename, "size": filesize})
        isblocking = self.getblocking()
        self.setblocking(True)  # 避免收不到file_ending_msg
        if self.sendMsg(file_header_msg):
            with open(path, 'rb') as fp:
                while True:
                    data = fp.read(2048)
                    if not data:
                        break
                    self.sendall(data)
            file_ending_msg = self.recvMsg()
            if file_ending_msg.isValid():
                received_filename = file_ending_msg.get("filename")
                received_filesize = file_ending_msg.get("size")
                if filename == received_filename and filesize == received_filesize:
                    self.setblocking(isblocking)
                    print("file sent: '{}'".format(filename))
                    return True
        self.setblocking(isblocking)
        return False

    def recvFile(self, download_dir=None) -> str:
        if download_dir is None:
            download_dir = SocketConfig.DEFAULT_DOWNLOAD_PATH
        isblocking = self.getblocking()
        self.setblocking(True)  # 避免收不到file_header_msg
        file_header_msg = self.recvMsg()
        if file_header_msg.isValid():
            filename = file_header_msg.get("filename")
            filesize = file_header_msg.get("size")
            if filename and filesize > 0:
                if not os.path.exists(download_dir):
                    os.makedirs(download_dir)
                down_path = os.path.join(download_dir, filename)
                received_size = 0
                with open(down_path, 'wb') as fp:
                    # TODO 异常处理
                    while received_size < filesize:
                        recv_size = min(filesize - received_size, SocketConfig.BUFFER_SIZE)
                        data = self.recv(recv_size)
                        fp.write(data)
                        received_size += len(data)
                file_ending_msg = Message.JsonMsg(1002, 0, {"filename": filename, "size": received_size})
                if self.sendMsg(file_ending_msg):
                    self.setblocking(isblocking)
                    print("file received: '{}'".format(down_path))
                    return down_path
        self.setblocking(isblocking)
        return ""

    def sendFiles(self, paths: List[str], filenames: List[str]) -> int:
        if len(paths) != len(filenames):
            return 0
        files_header_msg = Message.JsonMsg(1011, 0, {"count": len(paths)})
        if self.sendMsg(files_header_msg):
            countSuccess = 0
            for i in range(len(paths)):
                if self.sendFile(paths[i], filenames[i]):
                    countSuccess += 1
            return countSuccess
        return 0

    def recvFiles(self, download_dir=None) -> Tuple[List[str], int]:
        files_header_msg = self.recvMsg()
        if not files_header_msg.isValid():
            return [], 0
        fileAmount = files_header_msg.get("count")
        filepaths = []
        for i in range(fileAmount):
            filepath = self.recvFile(download_dir)
            if filepath:
                filepaths.append(filepath)
        return filepaths, fileAmount

    def createFileTranCon(self, ftpmode: int, port=0) -> "HSocketTcp":
        """Create a new socket for file transporting.

            :param ftpmode: PORT / PASV (just like FTP) 
            :param port: Only valiable in PORT mode. Provide port of file-transport-socket.
            :return: A new socket for file transporting.
        """
        if ftpmode == FTP_PORT:
            filesock = HSocketTcp()
            ip = self.getsockname()[0]
            filesock.bind((ip, port))
            filesock.listen(1)
            file_port_msg = Message.JsonMsg(0, 0, ip=ip, port=filesock.getsockname()[1])
            self.sendMsg(file_port_msg)
            transport_conn, addr = filesock.accept()
            return transport_conn
        elif ftpmode == FTP_PASV:
            file_port_msg = self.recvMsg()
            ip = file_port_msg.get("ip")
            port = file_port_msg.get("port")
            transport_sock = HSocketTcp()
            transport_sock.connect((ip, port))
            return transport_sock
        else:
            raise ValueError(f"invaliable ftpmode value '{ftpmode}'")


class HSocketUdp(socket.socket):
    def __init__(self):
        super().__init__(socket.AF_INET, socket.SOCK_DGRAM)

    def sendMsg(self, msg: "Message", address: Tuple[str, int]) -> bool:
        data = msg.to_bytes()
        return bool(self.sendto(data, address))

    def recvMsg(self) -> Tuple[Optional["Message"], Optional[Tuple[str, int]]]:
        try:
            data, from_ = self.recvfrom(65535)
        except ConnectionResetError:  # received an ICMP unreachable
            return None, None
        if data:
            return Message.from_bytes(data), from_
        else:
            return None, None
