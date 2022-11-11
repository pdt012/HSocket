# -*- coding: utf-8 -*-
from typing import Optional
import threading
from .socket import HSocketTcp, HSocketUdp, ClientTcpSocket, ClientUdpSocket
from .message import Header, Message

class HTcpP2PClient:
    def __init__(self):
        self.__tcp_socket: "HSocketTcp" = ClientTcpSocket()
        self.__tcp_socket.setblocking(True)
        self.__message_thread = threading.Thread(target=self.__recv_handle, daemon=True)

    def _socket(self) -> "HSocketTcp":
        return self.__tcp_socket

    def settimeout(self, timeout):
        self.__tcp_socket.settimeout(timeout)

    def connect(self, addr):
        self.__tcp_socket.connect(addr)
        self.__message_thread.start()

    def close(self):
        self.__tcp_socket.close()

    def isclosed(self) -> bool:
        return self.__tcp_socket.fileno() == -1

    def send(self, msg: "Message") -> bool:
        try:
            return self.__tcp_socket.sendMsg(msg)
        except ConnectionResetError:
            self.__message_thread.join()  # make sure that '_onDisconnected' only runs once
            if (not self.isclosed()):
                print("connection reset")
                self._onDisconnected()
                self.close()
            return False

    def __recv_handle(self):
        while not self.isclosed():
            try:
                msg = self.__tcp_socket.recvMsg()
            except TimeoutError:
                continue
            except ConnectionResetError:
                print("connection reset")
                self._onDisconnected()
                self.close()
                break
            else:
                self._messageHandle(msg)

    def _messageHandle(self, msg: "Message"):
        ...

    def _onDisconnected(self):
        pass


class HUdpP2PClient:
    def __init__(self):
        self.__udp_socket: "HSocketUdp" = ClientUdpSocket()
        self.__udp_socket.setblocking(True)
        self.peer_addr = None
        self.__running = False
        self.__message_thread = threading.Thread(target=self.__recv_handle, daemon=True)

    def settimeout(self, timeout):
        self.__udp_socket.settimeout(timeout)

    def close(self):
        self.__running = False
        self.__udp_socket.close()

    def isclosed(self) -> bool:
        return self.__udp_socket.fileno() == -1

    def start(self, sock_addr):
        if not self.__running:
            self.__udp_socket.bind(sock_addr)
            self.__running = True
            self.__message_thread.start()
        else:
            raise RuntimeError("Already started.")

    def setpeeraddr(self, peer_addr):
        self.peer_addr = peer_addr

    def send(self, msg: "Message") -> bool:
        return self.__udp_socket.sendMsg(msg, self.peer_addr)

    def __recv_handle(self):
        while self.__running:
            try:
                msg, addr = self.__udp_socket.recvMsg()
                if (addr != self.peer_addr):
                    continue
            except TimeoutError:
                continue
            else:
                self._messageHandle(msg)

    def _messageHandle(self, msg: "Message"):
        ...
