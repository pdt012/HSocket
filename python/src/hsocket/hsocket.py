# -*- coding: utf-8 -*-
from typing import Optional, Union, BinaryIO
import socket
import os
from .message import *


class SocketConfig:
    BUFFER_SIZE = 1024
    DEFAULT_DOWNLOAD_PATH = "download/"
    FILENAME_ENCODING = "utf-8"


class _HSocket(socket.socket):
    def __init__(self, family=-1, type_=-1, proto=-1, fileno=None):
        super().__init__(family, type_, proto, fileno)

    def isValid(self) -> bool:
        return self.fileno != -1


class HTcpSocket(_HSocket):
    def __init__(self, family=socket.AF_INET, fileno=None):
        super().__init__(family, socket.SOCK_STREAM, fileno=fileno)
    
    def accept(self) -> tuple["HTcpSocket", tuple[str, int]]:
        # Paraphrased from socket.socket.accept()
        fd, addr = self._accept()
        sock = HTcpSocket(self.family, fileno=fd)
        if socket.getdefaulttimeout() is None and self.gettimeout():
            sock.setblocking(True)
        return sock, addr

    def sendMsg(self, msg: Message):
        """发送一个数据包

        Raises:
            OSError: 套接字异常时抛出。
        """
        data = msg.toBytes()
        self.sendall(data)

    def recvMsg(self) -> Message:
        """尝试接收一个数据包

        Raises:
            TimeoutError: 阻塞模式下等待超时时抛出。
            OSError: 套接字异常时抛出。

        Returns:
            Message: 收到空报文时返回空Message
        """
        data = b""
        header = Header.fromBytes(self.recv(Header.HEADER_LENGTH))
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
        """发送一个文件

        Raises:
            OSError: 套接字异常或文件读取异常时抛出。

        Args:
            file (BinaryIO): 可读的文件对象
            filename (str): 文件名
        """
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
        """尝试接收一个文件

        Raises:
            TimeoutError: 阻塞模式下等待超时时抛出。
            OSError: 套接字异常或文件写入异常时抛出。

        Returns:
            str: 成功接收的文件路径，若接收失败则返回空字符串。
        """
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


class HUdpSocket(_HSocket):
    def __init__(self, family=socket.AF_INET, fileno=None):
        super().__init__(family, socket.SOCK_DGRAM, fileno=fileno)

    def sendMsg(self, msg: "Message", address: tuple[str, int]) -> bool:
        """发送一个数据包

        Args:
            msg (Message): 数据包
            address (tuple[str, int]): 目标地址

        Returns:
            bool: 数据是否全部发送
        """
        data = msg.toBytes()
        return self.sendto(data, address) == len(data)

    def recvMsg(self) -> tuple[Message, Optional[tuple[str, int]]]:
        """接收一个数据包

        Returns:
            tuple[Message, Optional[tuple[str, int]]]: 数据包(可能为Error包或空包)，源地址
        """
        try:
            data, from_ = self.recvfrom(65535)
        except ConnectionResetError:  # received an ICMP unreachable
            return Message(ContentType.ERROR_), None
        return Message.fromBytes(data), from_
