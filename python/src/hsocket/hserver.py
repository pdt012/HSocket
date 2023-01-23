# -*- coding: utf-8 -*-
import selectors
from typing import Callable
from abc import abstractmethod
from .hsocket import *


class HServerSelector:
    def __init__(self, messageHandle: Callable, onConnected: Callable, onDisconnected: Callable):
        self.messageHandle = messageHandle
        self.onDisconnected = onDisconnected
        self.onConnected = onConnected
        self.server_socket: "HTcpSocket" = None
        self.msgs: Dict["HTcpSocket", "Message"] = {}

    def start(self, addr, backlog=10):
        self.server_socket = HTcpSocket()
        self.server_socket.bind(addr)
        self.server_socket.setblocking(False)
        self.server_socket.listen(backlog)

        self.selector = selectors.DefaultSelector()
        self.selector.register(self.server_socket, selectors.EVENT_READ, self.callback_accept)

        print("server start at {}".format(addr))
        while True:
            events = self.selector.select()
            for key, mask in events:
                callback = key.data
                callback(key.fileobj)

    def stop(self):
        fobj_list = []
        for fd, key in self.selector.get_map().items():
            fobj_list.append(key.fileobj)
        for fobj in fobj_list:
            self.selector.unregister(fobj)
            fobj.close()
        self.selector.close()

    def callback_accept(self, server_socket: "HTcpSocket"):
        conn, addr = server_socket.accept()
        print("connected: {}".format(addr))
        conn.setblocking(False)
        self.msgs[conn] = None
        self.selector.register(conn, selectors.EVENT_READ, self.callback_read)
        self.onConnected(conn, addr)

    def callback_read(self, conn: "HTcpSocket"):
        if not conn.isValid():
            print("not a socket")
            self.selector.unregister(conn)
            del self.msgs[conn]
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
            self.selector.unregister(conn)
            conn.close()
            del self.msgs[conn]
            print("connection closed: {}".format(addr))
            self.onDisconnected(addr)  # disconnect callback

    def callback_write(self, conn: "HTcpSocket"):
        msg = self.msgs[conn]
        if msg:
            self.messageHandle(conn, msg)
            self.msgs[conn] = None
        self.selector.modify(conn, selectors.EVENT_READ, self.callback_read)

    def remove(self, conn: "HTcpSocket"):
        self.selector.unregister(conn)


class HTcpServer:
    def __init__(self):
        self.__selector = HServerSelector(self._messageHandle, self._onConnected, self._onDisconnected)

    def start(self, addr):
        self.__selector.start(addr)

    def close(self):
        self.__selector.stop()

    def remove(self, conn: "HTcpSocket"):
        self.__selector.remove(conn)

    @staticmethod
    def sendFile(self, conn: "HTcpSocket", path: str, filename: str) -> bool:
        isblocking = conn.getblocking()
        conn.setblocking(True)  # 避免引发BlockingError
        ret = conn.sendFile(path, filename)
        conn.setblocking(isblocking)
        return ret

    @staticmethod
    def recvFile(self, conn: "HTcpSocket") -> str:
        isblocking = conn.getblocking()
        conn.setblocking(True)  # 避免引发BlockingError
        ret = conn.recvFile()
        conn.setblocking(isblocking)
        return ret

    @staticmethod
    def sendFiles(self, conn: "HTcpSocket", paths: List[str], filenames: List[str]) -> int:
        isblocking = conn.getblocking()
        conn.setblocking(True)  # 避免引发BlockingError
        ret = conn.sendFiles(paths, filenames)
        conn.setblocking(isblocking)
        return ret

    @staticmethod
    def recvFiles(self, conn: "HTcpSocket") -> Tuple[List[str], int]:
        isblocking = conn.getblocking()
        conn.setblocking(True)  # 避免引发BlockingError
        ret = conn.recvFiles()
        conn.setblocking(isblocking)
        return ret

    @abstractmethod
    def _messageHandle(self, conn: "HTcpSocket", msg: "Message"):
        ...

    def _onConnected(self, conn: "HTcpSocket", addr):
        pass

    def _onDisconnected(self, addr):
        pass


class HUdpServer:
    def __init__(self):
        self.__udp_socket: "HUdpSocket" = None

    def socket(self) -> "HUdpSocket":
        return self.__udp_socket

    def start(self, addr):
        self.__udp_socket = HUdpSocket()
        self.__udp_socket.bind(addr)
        while True:
            if self.__udp_socket.fileno == -1:
                break
            msg, from_ = self.__udp_socket.recvMsg()
            self._messageHandle(msg, from_)
    
    def close(self):
        self.__udp_socket.close()

    def sendto(self, msg: "Message", c_addr):
        self.__udp_socket.sendMsg(msg, c_addr)
    
    @abstractmethod
    def _messageHandle(self, msg: "Message", c_addr):
        ...
