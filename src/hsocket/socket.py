# -*- coding: utf-8 -*-
from typing import Tuple, Optional, Union, List, Dict, Any
import socket
import os
from .message import Header, Message, MessageConfig


class SocketConfig:
    BUFFER_SIZE = 1024
    DEFAULT_DOWNLOAD_PATH = "download/"


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

    def sendFile(self, path: str, filename: str):
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
                    return True
        self.setblocking(isblocking)
        return False

    def recvFile(self) -> str:
        isblocking = self.getblocking()
        self.setblocking(True)  # 避免收不到file_header_msg
        file_header_msg = self.recvMsg()
        if file_header_msg.isValid():
            filename = file_header_msg.get("filename")
            filesize = file_header_msg.get("size")
            if filename and filesize > 0:
                if not os.path.exists(SocketConfig.DEFAULT_DOWNLOAD_PATH):
                    os.path.makedirs(SocketConfig.DEFAULT_DOWNLOAD_PATH)
                down_path = os.path.join(SocketConfig.DEFAULT_DOWNLOAD_PATH, filename)
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

    def recvFiles(self) -> Tuple[List[str], int]:
        files_header_msg = self.recvMsg()
        if not files_header_msg.isValid():
            return [], 0
        fileAmount = files_header_msg.get("count")
        filepaths = []
        for i in range(fileAmount):
            filepath = self.recvFile()
            if filepath:
                filepaths.append(filepath)
        return filepaths, fileAmount


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
