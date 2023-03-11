# -*- coding: utf-8 -*-
from typing import Optional, Union, BinaryIO
import socket
import os
from .message import *


class SocketConfig:
    recvBufferSize = 1024
    fileBufferSize = 2048
    downloadDirectory = "download/"


class _HSocket(socket.socket):
    def __init__(self, family=-1, type_=-1, proto=-1, fileno=None):
        super().__init__(family, type_, proto, fileno)

    def isValid(self) -> bool:
        """是否为有效的套接字"""
        return self.fileno() != -1


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

        Args:
            msg (Message): 发送的文件

        Raises:
            OSError: 套接字异常时抛出
        """
        self.sendall(msg.toBytes())

    def recvMsg(self) -> Message:
        """尝试接收一个数据包

        Raises:
            TimeoutError: 阻塞模式下等待超时时抛出
            OSError: 套接字异常时抛出
            EmptyMessageError: 收到空报文时抛出
            MessageHeaderError: 报头解析异常时抛出
            UnicodeDecodeError: 报文内容编码异常时抛出

        Returns:
            Message: 收到的报文
        """
        data = b""
        header = Header.fromBytes(self.recv(Header.HEADER_LENGTH))
        size = header.length
        while len(data) < size:  # 未接收完
            recv_size = min(size - len(data), SocketConfig.recvBufferSize)
            recv_data = self.recv(recv_size)
            data += recv_data
        if data:
            return Message.HeaderContent(header, data.decode("UTF-8"))
        else:
            return Message.HeaderContent(header, "")

    def sendFile(self, file: BinaryIO, filename: str):
        """发送一个文件

        Raises:
            OSError: 套接字异常或文件读取异常时抛出
            UnicodeEncodeError: 编码错误时抛出

        Args:
            file (BinaryIO): 可读的文件对象
            filename (str): 文件名
        """
        # get file size
        file.seek(0, os.SEEK_END)
        filesize = file.tell()
        file.seek(0, os.SEEK_SET)
        # file header
        self.sendall(filename.encode("UTF-8"))  # filename
        self.sendall(b'\0')  # name end
        self.sendall(filesize.to_bytes(4, 'little', signed=False))  # filesize
        # file content
        while True:
            data = file.read(SocketConfig.fileBufferSize)
            if not data:
                break
            self.sendall(data)

    def recvFile(self) -> str:
        """尝试接收一个文件

        Raises:
            TimeoutError: 阻塞模式下等待超时时抛出
            OSError: 套接字异常或文件写入异常时抛出
            UnicodeDecodeError: 编码错误时抛出

        Returns:
            str: 成功接收的文件路径，若接收失败则返回空字符串
        """
        # filename
        filename_b: bytes = b""
        while True:
            char = self.recv(1)
            if not char:  # empty data
                return ""
            elif char != b'\0':
                filename_b += char
            else:
                break
        filename = filename_b.decode("UTF-8")
        # filesize
        filesize_b = self.recv(4)
        filesize = int.from_bytes(filesize_b, 'little', signed=False)
        # file content
        if filename and filesize > 0:
            if not os.path.exists(SocketConfig.downloadDirectory):
                os.makedirs(SocketConfig.downloadDirectory)
            down_path = os.path.join(SocketConfig.downloadDirectory, filename)
            total_recv_size = 0
            with open(down_path, 'wb') as fp:
                while total_recv_size < filesize:
                    recv_size = min(filesize - total_recv_size, SocketConfig.recvBufferSize)
                    data = self.recv(recv_size)
                    fp.write(data)
                    total_recv_size += len(data)
            return down_path
        else:
            return ""


class HUdpSocket(_HSocket):
    def __init__(self, family=socket.AF_INET, fileno=None):
        super().__init__(family, socket.SOCK_DGRAM, fileno=fileno)

    def sendMsg(self, msg: "Message", address: tuple[str, int]) -> bool:
        """发送一个数据包

        Args:
            msg (Message): 发送的报文
            address (tuple[str, int]): 目标地址

        Returns:
            bool: 数据是否全部发送
        """
        data = msg.toBytes()
        return self.sendto(data, address) == len(data)

    def recvMsg(self) -> tuple[Message, tuple[str, int]]:
        """接收一个数据包

        Raises:
            TimeoutError: 阻塞模式下等待超时时抛出。
            EmptyMessageError: 收到空报文时抛出
            MessageHeaderError: 报头解析异常时抛出
            UnicodeDecodeError: 报文内容编码异常时抛出

        Returns:
            tuple[Message, tuple[str, int]]: 数据包，源地址
        """
        try:
            data, from_ = self.recvfrom(65535)
        except ConnectionResetError:  # received an ICMP unreachable
            raise EmptyMessageError()
        return Message.fromBytes(data), from_
