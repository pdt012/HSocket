# -*- coding: utf-8 -*-
from typing import Tuple, Optional, Union, List, Dict, Any, BinaryIO
import socket
import os
from .message import Header, Message, MessageConfig


class SocketConfig:
    BUFFER_SIZE = 1024
    DEFAULT_DOWNLOAD_PATH = "download/"
    FILENAME_ENCODING = "utf-8"


class HTcpSocket(socket.socket):
    def __init__(self, family=socket.AF_INET, type_=socket.SOCK_STREAM, proto=-1, fileno=None):
        super().__init__(family, type_, proto, fileno)
        self.sendfile

    def isValid(self) -> bool:
        return self.fileno != -1
    
    def accept(self) -> Tuple["HTcpSocket", Tuple[str, int]]:
        fd, addr = self._accept()
        sock = HTcpSocket(self.family, self.type, self.proto, fileno=fd)
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

    def sendFile(self, file: BinaryIO, filename: str):
        # get file size
        file.seek(0, os.SEEK_END)
        filesize = file.tell()
        file.seek(0, os.SEEK_SET)
        # file header
        self.sendall(filename.encode(SocketConfig.FILENAME_ENCODING))  # filename
        self.sendall(b'\0')  # name end
        self.sendall(filesize.to_bytes(4, 'little', signed=False))  # filesize
        # file content
        while True:
            data = file.read(2048)
            if not data:
                break
            self.sendall(data)

    def recvFile(self) -> str:
        filename_b: bytes = b""
        # filename
        while True:
            char = self.recv(1)
            if char != b'\0':
                filename_b += char
            else:
                break
        filename = filename_b.decode(SocketConfig.FILENAME_ENCODING)
        # filesize
        filesize_b = self.recv(4)
        filesize = int.from_bytes(filesize_b, 'little', signed=False)
        # file content
        if filename and filesize > 0:
            if not os.path.exists(SocketConfig.DEFAULT_DOWNLOAD_PATH):
                os.makedirs(SocketConfig.DEFAULT_DOWNLOAD_PATH)
            down_path = os.path.join(SocketConfig.DEFAULT_DOWNLOAD_PATH, filename)
            received_size = 0
            with open(down_path, 'wb') as fp:
                while received_size < filesize:
                    recv_size = min(filesize - received_size, SocketConfig.BUFFER_SIZE)
                    data = self.recv(recv_size)
                    fp.write(data)
                    received_size += len(data)
            return down_path
        else:
            return ""


class HUdpSocket(socket.socket):
    def __init__(self):
        super().__init__(socket.AF_INET, socket.SOCK_DGRAM)

    def isValid(self) -> bool:
        return self.fileno != -1

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
