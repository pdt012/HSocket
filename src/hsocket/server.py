# -*- coding: utf-8 -*-
import selectors
from typing import Callable
from abc import abstractmethod
from .socket import *


class HServerSelector:
    def __init__(self, messageHandle: Callable, onDisconnected: Callable):
        self.messageHandle = messageHandle
        self.onDisconnected = onDisconnected
        self.server_socket: "HSocketTcp" = None
        self.msgs: Dict["HSocketTcp", "Message"] = {}

    def start(self, addr, backlog=10):
        self.server_socket = HSocketTcp()
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
        # TODO: disconnect the remaining sockets before stop
        self.selector.close()

    def callback_accept(self, server_socket: "HSocketTcp"):
        conn, addr = server_socket.accept()
        print("connected: {}".format(addr))
        conn.setblocking(False)
        self.msgs[conn] = None
        self.selector.register(conn, selectors.EVENT_READ, self.callback_read)

    def callback_read(self, conn: "HSocketTcp"):
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

    def callback_write(self, conn: "HSocketTcp"):
        msg = self.msgs[conn]
        if msg:
            self.messageHandle(conn, msg)
            self.msgs[conn] = None
        self.selector.modify(conn, selectors.EVENT_READ, self.callback_read)


    def remove(self, conn: "HSocketTcp"):
        self.selector.unregister(conn)


class HTcpServer:
    def __init__(self):
        self.__selector = HServerSelector(self._messageHandle, self._onDisconnected)

    def start(self, addr):
        self.__selector.start(addr)

    def close(self):
        self.__selector.stop()

    @abstractmethod
    def _messageHandle(self, conn: "HSocketTcp", msg: "Message"):
        ...

    def _onDisconnected(self, addr):
        pass


class HUdpServer:
    def __init__(self):
        self.__udp_socket: "HSocketUdp" = None

    def start(self, addr):
        self.__udp_socket = HSocketUdp()
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
