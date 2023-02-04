# -*- coding: utf-8 -*-
from abc import abstractmethod
import threading
import socket
from .hsocket import *
from .message import *
from .hserver import BuiltInOpCode


class _HTcpClient:
    def __init__(self):
        self._tcp_socket: HTcpSocket = HTcpSocket()
        self._tcp_socket.setblocking(True)
        self._ft_server_ip = ""
        self._ft_server_port = 0

    def socket(self) -> HTcpSocket:
        return self._tcp_socket

    def settimeout(self, timeout):
        self._tcp_socket.settimeout(timeout)

    def connect(self, addr):
        self._tcp_socket.connect(addr)
        self._ft_server_ip = addr[0]

    def close(self):
        self._tcp_socket.close()

    def isclosed(self) -> bool:
        return not self._tcp_socket.isValid()

    @abstractmethod
    def sendmsg(self, msg: Message) -> bool:
        ...

    @abstractmethod
    def _get_ft_transfer_port(self) -> bool:
        ...

    def sendfile(self, path: str, filename: str):
        if not self._get_ft_transfer_port():
            return
        # send
        try:
            with HTcpSocket() as ft_socket:
                ft_socket.connect((self._ft_server_ip, self._ft_server_port))
                with open(path, 'rb') as fin:
                    ft_socket.sendFile(fin, filename)
        except OSError:
            return

    def recvfile(self) -> str:
        if not self._get_ft_transfer_port():
            return ""
        # recv
        try:
            with HTcpSocket() as ft_socket:
                ft_socket.connect((self._ft_server_ip, self._ft_server_port))
                down_path = ft_socket.recvFile()
            return down_path
        except OSError:
            return ""

    def sendfiles(self, paths: list[str], filenames: list[str]) -> int:
        if not self._get_ft_transfer_port():
            return 0
        if len(paths) != len(filenames):
            return 0
        # send
        count_sent = 0
        try:
            with HTcpSocket() as ft_socket:
                ft_socket.connect((self._ft_server_ip, self._ft_server_port))
                files_header_msg = Message.JsonMsg(BuiltInOpCode.FT_SEND_FILES_HEADER, 0, {"file_count": len(paths)})
                ft_socket.sendMsg(files_header_msg)
                for i in range(len(paths)):
                    path = paths[i]
                    filename = filenames[i]
                    with open(path, 'rb') as fin:
                        ft_socket.sendFile(fin, filename)
                        count_sent += 1
            return count_sent
        except OSError:
            return count_sent

    def recvfiles(self) -> list[str]:
        if not self._get_ft_transfer_port():
            return []
        # recv
        down_path_list = []
        try:
            with HTcpSocket() as ft_socket:
                ft_socket.connect((self._ft_server_ip, self._ft_server_port))
                files_header_msg = ft_socket.recvMsg()
                file_count = files_header_msg.get("file_count")
                for i in range(file_count):
                    path = ft_socket.recvFile()
                    if path:
                        down_path_list.append(path)
            return down_path_list
        except OSError:
            return down_path_list

    def _onDisconnected(self):
        pass


class HTcpChannelClient(_HTcpClient):
    def __init__(self):
        super().__init__()
        self.__th_message = threading.Thread(target=self.__message_handle, daemon=True)
        self.__con_ft_port = threading.Condition()
        self.__ft_timeout = 15

    def connect(self, addr):
        super().connect(addr)
        self.__th_message.start()

    def sendmsg(self, msg: Message) -> bool:
        try:
            self._tcp_socket.sendMsg(msg)
        except ConnectionResetError:
            self.__th_message.join()  # make sure that '_onDisconnected' only runs once
            if not self.isclosed():
                print("connection reset")
                self._onDisconnected()
                self.close()
            return False
        return True

    def set_ft_timeout(self, sec):
        self.__ft_timeout = sec

    def _get_ft_transfer_port(self) -> bool:
        success = self.__con_ft_port.wait(self.__ft_timeout)  # wait for an FT_TRANSFER_PORT reply
        return success

    def __message_handle(self):
        while not self.isclosed():
            try:
                msg = self._tcp_socket.recvMsg()
            except TimeoutError:
                continue
            except ConnectionResetError:
                print("connection reset")
                self._onDisconnected()
                self.close()
                break
            else:
                if msg.opcode() == BuiltInOpCode.FT_TRANSFER_PORT:
                    self._ft_server_port = msg.get("port")
                    self.__con_ft_port.notify()
                    continue
                self._onMessageReceived(msg)

    @abstractmethod
    def _onMessageReceived(self, msg: Message):
        ...


class HTcpReqResClient(_HTcpClient):
    def __init__(self):
        super().__init__()

    def sendmsg(self, msg: Message) -> bool:
        try:
            self._tcp_socket.sendMsg(msg)
        except ConnectionResetError:
            if not self.isclosed():
                print("connection reset")
                self._onDisconnected()
                self.close()
            return False
        return True

    def request(self, msg: Message) -> Message:
        if self.sendmsg(msg):
            try:
                response = self._tcp_socket.recvMsg()
            except TimeoutError:
                return Message(ContentType.ERROR_)
            except ConnectionResetError:
                print("connection reset")
                self._onDisconnected()
                self.close()
                return Message(ContentType.ERROR_)
            else:
                return response
        return Message(ContentType.ERROR_)

    def _get_ft_transfer_port(self) -> bool:
        try:
            msg = self._tcp_socket.recvMsg()
            if msg.opcode() == BuiltInOpCode.FT_TRANSFER_PORT:
                self._ft_server_port = msg.get("port")
                return True
            else:
                return False
        except OSError:
            return False


class _HUdpClient:
    def __init__(self, addr):
        self._udp_socket: HUdpSocket = HUdpSocket()
        self._udp_socket.setblocking(True)
        self._peer_addr = addr

    def socket(self) -> HUdpSocket:
        return self._udp_socket

    def settimeout(self, timeout):
        self._udp_socket.settimeout(timeout)

    def close(self):
        self._udp_socket.close()

    def isclosed(self) -> bool:
        return not self._udp_socket.isValid()

    def sendmsg(self, msg: Message) -> bool:
        return self._udp_socket.sendMsg(msg, self._peer_addr)


class HUdpChannelClient(_HUdpClient):
    def __init__(self, addr):
        super().__init__(addr)
        self.__running = False
        self.__th_message = threading.Thread(target=self.__message_handle, daemon=True)

    def close(self):
        self.__running = False
        super().close()

    def sendmsg(self, msg: Message) -> bool:
        ret = super().sendmsg(msg)
        # recvMsg before sendMsg will cause WinError10022.
        # So start the message thread after the first call of send.
        if not self.__running:
            self.__running = True
            self.__th_message.start()
        return ret

    def __message_handle(self):
        while not self.isclosed():
            try:
                msg, addr = self._udp_socket.recvMsg()
            except TimeoutError:
                continue
            else:
                self._onMessageReceived(msg)

    @abstractmethod
    def _onMessageReceived(self, msg: Message):
        ...


class HUdpReqResClient(_HUdpClient):
    def __init__(self, addr):
        super().__init__(addr)

    def request(self, msg: Message) -> Optional[Message]:
        try:
            self._udp_socket.sendMsg(msg, self._peer_addr)
            response, addr = self._udp_socket.recvMsg()
        except TimeoutError:
            return None
        else:
            return response
