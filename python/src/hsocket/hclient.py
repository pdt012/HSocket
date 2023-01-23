# -*- coding: utf-8 -*-
from typing import Optional
import threading
import socket
from enum import Enum, auto
from .hsocket import HTcpSocket, HUdpSocket
from .message import Header, Message


class ClientMode(Enum):
    SYNCHRONOUS = auto()  # The client send a request and get the response in the same thread.
    ASYNCHRONOUS = auto()  # The client send and receive in two threads.


class HTcpClient:
    def __init__(self, mode: ClientMode = ClientMode.SYNCHRONOUS):
        self.__tcp_socket: "HTcpSocket" = HTcpSocket()
        self.__tcp_socket.setblocking(True)
        self.__mode = mode
        if self.__mode is ClientMode.ASYNCHRONOUS:
            self.__message_thread = threading.Thread(target=self.__recv_handle, daemon=True)

    def socket(self) -> "HTcpSocket":
        return self.__tcp_socket

    def settimeout(self, timeout):
        self.__tcp_socket.settimeout(timeout)

    def connect(self, addr):
        self.__tcp_socket.connect(addr)
        if self.__mode is ClientMode.ASYNCHRONOUS:
            self.__message_thread.start()

    def close(self):
        self.__tcp_socket.close()

    def isclosed(self) -> bool:
        return self.__tcp_socket.fileno() == -1

    def send(self, msg: "Message") -> bool:
        try:
            return self.__tcp_socket.sendMsg(msg)
        except ConnectionResetError:
            if self.__mode is ClientMode.ASYNCHRONOUS:
                self.__message_thread.join()  # make sure that '_onDisconnected' only runs once
            if (not self.isclosed()):
                print("connection reset")
                self._onDisconnected()
                self.close()
            return False

    def request(self, msg: "Message") -> Optional["Message"]:
        if self.__mode is ClientMode.ASYNCHRONOUS:
            raise RuntimeError("'request' is not available in ASYNCHRONOUS mode. Please use 'send' instead")
        if (self.send(msg)):
            try:
                response = self.__tcp_socket.recvMsg()
            except TimeoutError:
                return None
            except ConnectionResetError:
                print("connection reset")
                self._onDisconnected()
                self.close()
                return None
            else:
                return response
        return None

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


class HUdpClient:
    def __init__(self, addr, mode: ClientMode = ClientMode.SYNCHRONOUS):
        self.__udp_socket: "HUdpSocket" = HUdpSocket()
        self.__udp_socket.setblocking(True)
        self.__mode = mode
        self._peer_addr = addr
        if self.__mode is ClientMode.ASYNCHRONOUS:
            self.__running = False
            self.__message_thread = threading.Thread(target=self.__recv_handle, daemon=True)

    def socket(self) -> "HUdpSocket":
        return self.__udp_socket

    def settimeout(self, timeout):
        self.__udp_socket.settimeout(timeout)

    def close(self):
        if self.__mode is ClientMode.ASYNCHRONOUS:
            self.__running = False
        self.__udp_socket.close()

    def isclosed(self) -> bool:
        return self.__udp_socket.fileno() == -1

    def send(self, msg: "Message") -> bool:
        ret = self.__udp_socket.sendMsg(msg, self._peer_addr)
        # recvMsg before sendMsg will cause WinError10022.
        # So start the message thread after the first call of send.
        if self.__mode is ClientMode.ASYNCHRONOUS and not self.__running:
            self.__running = True
            self.__message_thread.start()
        return ret

    def request(self, msg: "Message") -> Optional["Message"]:
        if self.__mode is ClientMode.ASYNCHRONOUS:
            raise RuntimeError("'request' is not available in ASYNCHRONOUS mode. Please use 'send' instead")
        try:
            self.__udp_socket.sendMsg(msg, self._peer_addr)
            response, addr = self.__udp_socket.recvMsg()
        except TimeoutError:
            return None
        else:
            return response

    def __recv_handle(self):
        while self.__running:
            try:
                msg, addr = self.__udp_socket.recvMsg()
            except TimeoutError:
                continue
            else:
                self._messageHandle(msg)

    def _messageHandle(self, msg: "Message"):
        ...
