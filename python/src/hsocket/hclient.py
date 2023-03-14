# -*- coding: utf-8 -*-
from abc import abstractmethod
from typing import Callable
import threading
from .hsocket import *
from .message import *
from .hserver import BuiltInOpCode


class _HTcpClient:
    OnConnectedCallback = Callable[[], None]
    OnDisconnectedCallback = Callable[[], None]

    def __init__(self):
        self._tcp_socket: HTcpSocket = HTcpSocket()
        self._tcp_socket.setblocking(True)
        self._ft_server_ip = ""
        self._ft_server_port = 0

        self.__onConnectedCallback: Optional[self.OnConnectedCallback] = None
        self.__onDisconnectedCallback: Optional[self.OnDisconnectedCallback] = None

    def socket(self) -> HTcpSocket:
        return self._tcp_socket

    def settimeout(self, timeout):
        self._tcp_socket.settimeout(timeout)

    def connect(self, addr):
        self._tcp_socket.connect(addr)
        self._ft_server_ip = addr[0]
        self._onConnected()

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
        with HTcpSocket() as ft_socket:
            try:
                ft_socket.connect((self._ft_server_ip, self._ft_server_port))
            except ConnectionError:
                return
            try:
                fin = open(path, 'rb')
            except OSError as e:  # file error
                print(e)
                return
            try:
                ft_socket.sendFile(fin, filename)
            except OSError:
                return
            finally:
                fin.close()

    def recvfile(self) -> str:
        if not self._get_ft_transfer_port():
            return ""
        # recv
        with HTcpSocket() as ft_socket:
            try:
                ft_socket.connect((self._ft_server_ip, self._ft_server_port))
                down_path = ft_socket.recvFile()
            except OSError:
                return ""
        return down_path

    def sendfiles(self, paths: list[str], filenames: list[str]) -> list[str]:
        if not self._get_ft_transfer_port():
            return []
        # send
        succeed_path_list = []
        with HTcpSocket() as ft_socket:
            try:
                ft_socket.connect((self._ft_server_ip, self._ft_server_port))
                ft_socket.sendFiles(paths, filenames, succeed_path_list)
            except ValueError:
                raise
            except OSError:
                pass
        return succeed_path_list

    def recvfiles(self) -> list[str]:
        if not self._get_ft_transfer_port():
            return []
        # recv
        download_path_list = []
        with HTcpSocket() as ft_socket:
            try:
                ft_socket.connect((self._ft_server_ip, self._ft_server_port))
                ft_socket.recvFiles(download_path_list)
            except OSError:
                pass
        return download_path_list

    def setOnConnectedCallback(self, callback: OnConnectedCallback):
        self.__onConnectedCallback = callback

    def setOnDisconnectedCallback(self, callback: OnDisconnectedCallback):
        self.__onDisconnectedCallback = callback

    def _onConnected(self):
        if self.__onConnectedCallback:
            self.__onConnectedCallback()

    def _onDisconnected(self):
        if self.__onDisconnectedCallback:
            self.__onDisconnectedCallback()


class HTcpChannelClient(_HTcpClient):
    OnMessageReceivedCallback = Callable[[Message], None]
    OnMsgRecvByOpCodeCallback = Callable[[Message], bool]  # 返回False时会继续进行OnMessageReceivedCallback

    def __init__(self):
        super().__init__()
        self.__th_message = threading.Thread(target=self.__message_handle, daemon=True)
        self.__con_ft_port = threading.Condition()
        self.__ft_timeout = 15

        self.__onMessageReceivedCallback: Optional[self.OnMessageReceivedCallback] = None
        self.__onMsgRecvByOpCodeCallbackDict: dict[int, self.OnMsgRecvByOpCodeCallback] = {}

    def connect(self, addr):
        super().connect(addr)
        self.__th_message.start()

    def sendmsg(self, msg: Message) -> bool:
        try:
            self._tcp_socket.sendMsg(msg)
        except OSError:
            self.__th_message.join()  # make sure that '_onDisconnected' only runs once
            if not self.isclosed():
                print("connection error")
                self._onDisconnected()
                self.close()
            return False
        return True

    def set_ft_timeout(self, sec):
        self.__ft_timeout = sec

    def _get_ft_transfer_port(self) -> bool:
        self.__con_ft_port.acquire()
        success = self.__con_ft_port.wait(self.__ft_timeout)  # wait for an FT_TRANSFER_PORT reply
        self.__con_ft_port.release()
        return success

    def __message_handle(self):
        while not self.isclosed():
            try:
                msg = self._tcp_socket.recvMsg()
            except TimeoutError:
                continue
            except OSError:
                print("connection error")
                self._onDisconnected()
                self.close()
                break
            except MessageError:
                print("message error")
                self._onDisconnected()
                self.close()
                break
            else:
                if msg.opcode() == BuiltInOpCode.FT_TRANSFER_PORT:
                    self._ft_server_port = msg.get("port")
                    self.__con_ft_port.acquire()
                    self.__con_ft_port.notify()
                    self.__con_ft_port.release()
                    continue
                self._onMessageReceived(msg)

    def setOnMsgRecvByOpCodeCallback(self, opcode: int, callback: OnMessageReceivedCallback):
        self.__onMsgRecvByOpCodeCallbackDict[opcode] = callback

    def popOnMsgRecvByOpCodeCallback(self, opcode: int):
        self.__onMsgRecvByOpCodeCallbackDict.pop(opcode)

    def setOnMessageReceivedCallback(self, callback: OnMessageReceivedCallback):
        self.__onMessageReceivedCallback = callback

    def _onMessageReceived(self, msg: Message):
        opcode = msg.opcode()
        callback = self.__onMsgRecvByOpCodeCallbackDict.get(opcode)
        if callback is not None:
            finished = callback(msg)
            if finished:
                return
        if self.__onMessageReceivedCallback:
            self.__onMessageReceivedCallback(msg)


class HTcpReqResClient(_HTcpClient):
    def __init__(self):
        super().__init__()

    def sendmsg(self, msg: Message) -> bool:
        try:
            self._tcp_socket.sendMsg(msg)
        except OSError:
            if not self.isclosed():
                print("connection error")
                self._onDisconnected()
                self.close()
            return False
        return True

    def request(self, msg: Message) -> Optional[Message]:
        if self.sendmsg(msg):
            flag_error = False
            try:
                response = self._tcp_socket.recvMsg()
            except TimeoutError:
                print("time out")
                flag_error = True  # 如果不断开，可能会在下次request时收到这次的response
            except OSError:
                print("connection error")
                flag_error = True
            except MessageError:
                print("message error")
                flag_error = True  # 收到空报文时断开
            if flag_error:
                self._onDisconnected()
                self.close()
                return None
            else:
                return response
        return None

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
        except MessageError:
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
    OnMessageReceivedCallback = Callable[[Message], None]
    OnMsgRecvByOpCodeCallback = Callable[[Message], bool]  # 返回False时会继续进行OnMessageReceivedCallback

    def __init__(self, addr):
        super().__init__(addr)
        self.__running = False
        self.__th_message = threading.Thread(target=self.__message_handle, daemon=True)

        self.__onMessageReceivedCallback: Optional[self.OnMessageReceivedCallback] = None
        self.__onMsgRecvByOpCodeCallbackDict: dict[int, self.OnMsgRecvByOpCodeCallback] = {}

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
            except MessageError:
                continue
            else:
                self._onMessageReceived(msg)

    def setOnMsgRecvByOpCodeCallback(self, opcode: int, callback: OnMessageReceivedCallback):
        self.__onMsgRecvByOpCodeCallbackDict[opcode] = callback

    def popOnMsgRecvByOpCodeCallback(self, opcode: int):
        self.__onMsgRecvByOpCodeCallbackDict.pop(opcode)

    def setOnMessageReceivedCallback(self, callback: OnMessageReceivedCallback):
        self.__onMessageReceivedCallback = callback

    def _onMessageReceived(self, msg: Message):
        opcode = msg.opcode()
        callback = self.__onMsgRecvByOpCodeCallbackDict.get(opcode)
        if callback is not None:
            finished = callback(msg)
            if finished:
                return
        if self.__onMessageReceivedCallback:
            self.__onMessageReceivedCallback(msg)


class HUdpReqResClient(_HUdpClient):
    def __init__(self, addr):
        super().__init__(addr)

    def request(self, msg: Message) -> Optional[Message]:
        try:
            self._udp_socket.sendMsg(msg, self._peer_addr)
            response, addr = self._udp_socket.recvMsg()
        except TimeoutError:
            return None
        except MessageError:
            return None
        else:
            return response
