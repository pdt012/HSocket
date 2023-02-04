# -*- coding: utf-8 -*-
import selectors
from typing import Callable
from abc import abstractmethod
from .hsocket import *
from .message import *


class BuiltInOpCode(IntEnum):
    FT_TRANSFER_PORT = 60020  # 文件传输端口 {"port": port}
    FT_SEND_FILES_HEADER = 62000  # 多文件传输时头部信息 {"file_count": 文件数}


class _HServerSelector:
    def __init__(self, messageHandle: Callable, onConnected: Callable, onDisconnected: Callable):
        self.messageHandle = messageHandle
        self.onDisconnected = onDisconnected
        self.onConnected = onConnected
        self.server_socket = HTcpSocket()
        self.msgs: dict[HTcpSocket, Message] = {}
        self.running = False

    def start(self, addr, backlog=10):
        self.server_socket.bind(addr)
        self.server_socket.setblocking(False)
        self.server_socket.listen(backlog)

        self.selector = selectors.DefaultSelector()
        self.selector.register(self.server_socket, selectors.EVENT_READ, self.callback_accept)

        print("server start at {}".format(addr))
        self.running = True
        self.run()

    def run(self):
        while self.running:
            events = self.selector.select()
            for key, mask in events:
                callback = key.data
                callback(key.fileobj)

    def stop(self):
        self.running = False
        fobj_list = []
        for fd, key in self.selector.get_map().items():
            fobj_list.append(key.fileobj)
        for fobj in fobj_list:
            self.selector.unregister(fobj)
            fobj.close()
        self.selector.close()

    def callback_accept(self, server_socket: HTcpSocket):
        conn, addr = server_socket.accept()
        print("connected: {}".format(addr))
        conn.setblocking(False)
        self.msgs[conn] = None
        self.selector.register(conn, selectors.EVENT_READ, self.callback_read)
        self.onConnected(conn, addr)

    def callback_read(self, conn: HTcpSocket):
        if not conn.isValid():
            print("not a socket")
            self.remove(conn)
            return
        addr = conn.getpeername()
        try:
            msg = conn.recvMsg()  # receive msg
        except ConnectionResetError:
            print("connection reset: {}".format(addr))
            msg = None
        if msg and msg.isValid():
            self.msgs[conn] = msg
            self.selector.modify(conn, selectors.EVENT_WRITE, self.callback_write)
        else:  # empty msg or error
            self.remove(conn)
            print("connection closed: {}".format(addr))
            self.onDisconnected(addr)  # disconnect callback

    def callback_write(self, conn: HTcpSocket):
        msg = self.msgs[conn]
        if msg:
            self.messageHandle(conn, msg)
            self.msgs[conn] = None
        if not conn.isValid():  # may be disconnected in messageHandle
            self.remove(conn)
            return
        self.selector.modify(conn, selectors.EVENT_READ, self.callback_read)

    def remove(self, conn: HTcpSocket):
        self.selector.unregister(conn)
        del self.msgs[conn]


class HTcpServer:
    def __init__(self):
        self.__ip: str = ""
        self.__selector = _HServerSelector(self._messageHandle, self._onConnected, self._onDisconnected)
        self.__ft_timeout = 15

    def startserver(self, addr):
        self.__ip = addr[0]
        self.__selector.start(addr)

    def closeserver(self):
        self.__selector.stop()

    def closeconn(self, conn: HTcpSocket):
        """主动关闭一个连接，不会触发onDisconnected"""
        conn.close()

    def set_ft_timeout(self, sec):
        self.__ft_timeout = sec

    def _get_ft_transfer_conn(self, conn: HTcpSocket) -> HTcpSocket:
        with HTcpSocket() as ft_socket:
            ft_socket.bind((self.__ip, 0))
            port = ft_socket.getsockname()[1]
            conn.sendMsg(Message.JsonMsg(BuiltInOpCode.FT_TRANSFER_PORT, port=port))
            ft_socket.settimeout(self.__ft_timeout)
            ft_socket.listen(1)
            c_socket, c_addr = ft_socket.accept()
            return c_socket

    def sendfile(self, conn: HTcpSocket, path: str, filename: str):
        try:
            with self._get_ft_transfer_conn(conn) as c_socket:
                with open(path, 'rb') as fin:
                    c_socket.sendFile(fin, filename)
        except OSError:
            return

    def recvfile(self, conn: HTcpSocket) -> str:
        try:
            with self._get_ft_transfer_conn(conn) as c_socket:
                down_path = c_socket.recvFile()
                return down_path
        except OSError:
            return ""

    def sendfiles(self, conn: HTcpSocket, paths: list[str], filenames: list[str]) -> int:
        if len(paths) != len(filenames):
            return 0
        count_sent = 0
        try:
            with self._get_ft_transfer_conn(conn) as c_socket:
                files_header_msg = Message.JsonMsg(BuiltInOpCode.FT_SEND_FILES_HEADER, 0, {"file_count": len(paths)})
                c_socket.sendMsg(files_header_msg)
                for i in range(len(paths)):
                    path = paths[i]
                    filename = filenames[i]
                    with open(path, 'rb') as fin:
                        c_socket.sendFile(fin, filename)
                        count_sent += 1
                return count_sent
        except OSError:
            return count_sent

    def recvfiles(self, conn: HTcpSocket) -> list[str]:
        down_path_list = []
        try:
            with self._get_ft_transfer_conn(conn) as c_socket:
                files_header_msg = c_socket.recvMsg()
                file_count = files_header_msg.get("file_count")
                for i in range(file_count):
                    path = c_socket.recvFile()
                    if path:
                        down_path_list.append(path)
                return down_path_list
        except OSError:
            return down_path_list

    @abstractmethod
    def _messageHandle(self, conn: HTcpSocket, msg: Message):
        ...

    def _onConnected(self, conn: HTcpSocket, addr):
        pass

    def _onDisconnected(self, addr):
        pass


class HUdpServer:
    def __init__(self):
        self.__udp_socket = HUdpSocket()

    def socket(self) -> HUdpSocket:
        return self.__udp_socket

    def startserver(self, addr):
        self.__udp_socket.bind(addr)
        while self.__udp_socket.isValid():
            msg, from_ = self.__udp_socket.recvMsg()
            self._messageHandle(msg, from_)

    def closeserver(self):
        self.__udp_socket.close()

    def sendto(self, msg: Message, c_addr):
        self.__udp_socket.sendMsg(msg, c_addr)

    @abstractmethod
    def _messageHandle(self, msg: Message, c_addr):
        ...
