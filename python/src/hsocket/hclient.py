# -*- coding: utf-8 -*-
from typing import Optional
import threading
import socket
from enum import Enum, auto
from .hsocket import *
from .message import *


class ClientMode(Enum):
    SYNCHRONOUS = auto()  # The client send a request and get the response in the same thread.
    ASYNCHRONOUS = auto()  # The client send and receive in two threads.


class HTcpClient:
    def __init__(self, mode: ClientMode = ClientMode.SYNCHRONOUS):
        self.__tcp_socket: HTcpSocket = HTcpSocket()
        self.__tcp_socket.setblocking(True)
        self.__mode = mode
        if self.__mode is ClientMode.ASYNCHRONOUS:
            self.__message_thread = threading.Thread(target=self.__recv_handle, daemon=True)
            self.__ftp_pacv_con = threading.Condition()
        self.__ftp_server_ip = ""
        self.__ftp_server_port = 0

    def socket(self) -> HTcpSocket:
        return self.__tcp_socket

    def settimeout(self, timeout):
        self.__tcp_socket.settimeout(timeout)

    def connect(self, addr):
        self.__tcp_socket.connect(addr)
        self.__ftp_server_ip = addr[0]
        if self.__mode is ClientMode.ASYNCHRONOUS:
            self.__message_thread.start()

    def close(self):
        self.__tcp_socket.close()

    def isclosed(self) -> bool:
        return not self.__tcp_socket.isValid()

    def sendmsg(self, msg: Message) -> bool:
        try:
            self.__tcp_socket.sendMsg(msg)
        except ConnectionResetError:
            if self.__mode is ClientMode.ASYNCHRONOUS:
                self.__message_thread.join()  # make sure that '_onDisconnected' only runs once
            if (not self.isclosed()):
                print("connection reset")
                self._onDisconnected()
                self.close()
            return False
        return True

    def request(self, msg: Message) -> Optional[Message]:
        if self.__mode is ClientMode.ASYNCHRONOUS:
            raise RuntimeError("'request' is not available in ASYNCHRONOUS mode. Please use 'send' instead")
        if (self.sendmsg(msg)):
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
    
    def sendfile(self, path: str, filename: str):
        # get server's tranfer port
        if self.__mode is ClientMode.ASYNCHRONOUS:
            self.__ftp_pacv_con.wait(15)  # wait for a FTP_TRANSFER_PORT reply
        else:
            msg = self.__tcp_socket.recvMsg()
            if msg.contenttype() == ContentType.FT_TRANSFER_PORT:
                self.__ftp_server_port = msg.statuscode()
        # send
        with HTcpSocket() as ftp_socket:
            ftp_socket.connect((self.__ftp_server_ip, self.__ftp_server_port))
            with open(path, 'rb') as fin:
                ftp_socket.sendFile(fin, filename)
    
    def recvfile(self) -> str:
        # get server's tranfer port
        if self.__mode is ClientMode.ASYNCHRONOUS:
            self.__ftp_pacv_con.wait(15)  # wait for a FTP_TRANSFER_PORT reply
        else:
            msg = self.__tcp_socket.recvMsg()
            if msg.contenttype() == ContentType.FT_TRANSFER_PORT:
                self.__ftp_server_port = msg.statuscode()
            else:
                 return ""
        # recv
        with HTcpSocket() as ftp_socket:
            ftp_socket.connect((self.__ftp_server_ip, self.__ftp_server_port))
            down_path = ftp_socket.recvFile()
        return down_path

    def sendfiles(self, paths: list[str], filenames: list[str]) -> int:
        if len(paths) != len(filenames):
            return 0
        # get server's tranfer port
        if self.__mode is ClientMode.ASYNCHRONOUS:
            self.__ftp_pacv_con.wait(15)  # wait for a FTP_TRANSFER_PORT reply
        else:
            msg = self.__tcp_socket.recvMsg()
            if msg.contenttype() == ContentType.FT_TRANSFER_PORT:
                self.__ftp_server_port = msg.statuscode()
            else:
                 return 0
        # send
        count_sent = 0
        with HTcpSocket() as ftp_socket:
            ftp_socket.connect((self.__ftp_server_ip, self.__ftp_server_port))
            files_header_msg = Message.JsonMsg(0, 0, {"file_count": len(paths)})
            ftp_socket.sendMsg(files_header_msg)
            for i in range(len(paths)):
                path = paths[i]
                filename = filenames[i]
                with open(path, 'rb') as fin:
                    ftp_socket.sendFile(fin, filename)
                    count_sent += 1
        return count_sent

    def recvfiles(self) -> list[str]:
        # get server's tranfer port
        if self.__mode is ClientMode.ASYNCHRONOUS:
            self.__ftp_pacv_con.wait(15)  # wait for a FTP_TRANSFER_PORT reply
        else:
            msg = self.__tcp_socket.recvMsg()
            if msg.contenttype() == ContentType.FT_TRANSFER_PORT:
                self.__ftp_server_port = msg.statuscode()
        # recv
        down_path_list = []
        with HTcpSocket() as ftp_socket:
            ftp_socket.connect((self.__ftp_server_ip, self.__ftp_server_port))
            files_header_msg = ftp_socket.recvMsg()
            file_count = files_header_msg.get("file_count")
            for i in range(file_count):
                path = ftp_socket.recvFile()
                if path:
                    down_path_list.append(path)
        return down_path_list

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
                if msg.contenttype() == ContentType.FT_TRANSFER_PORT:  # file
                    self.__ftp_server_port = msg.statuscode()
                    self.__ftp_pacv_con.notify()
                    continue
                self._messageHandle(msg)

    def _messageHandle(self, msg: Message):
        ...

    def _onDisconnected(self):
        pass


class HUdpClient:
    def __init__(self, addr, mode: ClientMode = ClientMode.SYNCHRONOUS):
        self.__udp_socket: HUdpSocket = HUdpSocket()
        self.__udp_socket.setblocking(True)
        self.__mode = mode
        self._peer_addr = addr
        if self.__mode is ClientMode.ASYNCHRONOUS:
            self.__running = False
            self.__message_thread = threading.Thread(target=self.__recv_handle, daemon=True)

    def socket(self) -> HUdpSocket:
        return self.__udp_socket

    def settimeout(self, timeout):
        self.__udp_socket.settimeout(timeout)

    def close(self):
        if self.__mode is ClientMode.ASYNCHRONOUS:
            self.__running = False
        self.__udp_socket.close()

    def isclosed(self) -> bool:
        return not self.__udp_socket.isValid()

    def sendmsg(self, msg: Message) -> bool:
        ret = self.__udp_socket.sendMsg(msg, self._peer_addr)
        # recvMsg before sendMsg will cause WinError10022.
        # So start the message thread after the first call of send.
        if self.__mode is ClientMode.ASYNCHRONOUS and not self.__running:
            self.__running = True
            self.__message_thread.start()
        return ret

    def request(self, msg: Message) -> Optional[Message]:
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

    def _messageHandle(self, msg: Message):
        ...
