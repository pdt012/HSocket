# -*- coding: utf-8 -*-
import selectors
from socketserver import ThreadingTCPServer, BaseRequestHandler
from abc import abstractmethod
from typing import Callable
from .hsocket import *
from .message import *


class BuiltInOpCode(IntEnum):
    FT_TRANSFER_PORT = 60020  # 文件传输端口 {"port": port}
    FT_SEND_FILES_HEADER = 62000  # 多文件传输时头部信息 {"file_count": 文件数}


class __HTcpServer:
    OnMsgRecvByOpCodeCallback = Callable[[HTcpSocket, Message], bool]  # 返回False时会继续进行OnMessageReceivedCallback
    OnMessageReceivedCallback = Callable[[HTcpSocket, Message], None]
    OnConnectedCallback = Callable[[HTcpSocket, tuple], None]
    OnDisconnectedCallback = Callable[[HTcpSocket, tuple], None]

    def __init__(self, addr):
        self._address: str = addr
        self.__ft_timeout = 15

        self.__onMsgRecvByOpCodeCallbackDict: dict[int, self.OnMsgRecvByOpCodeCallback] = {}
        self.__onMessageReceivedCallback: Optional[self.OnMessageReceivedCallback] = None
        self.__onConnectedCallback: Optional[self.OnConnectedCallback] = None
        self.__onDisconnectedCallback: Optional[self.OnDisconnectedCallback] = None

    @abstractmethod
    def startserver(self):
        """启动server"""
        ...

    @abstractmethod
    def closeserver(self):
        """关闭server"""
        ...

    def closeconn(self, conn: HTcpSocket):
        """主动关闭一个连接"""
        conn.close()

    def set_ft_timeout(self, sec):
        """设置文件传输超时时间"""
        self.__ft_timeout = sec

    def _get_ft_transfer_conn(self, conn: HTcpSocket) -> Optional[HTcpSocket]:
        with HTcpSocket() as ft_socket:
            try:
                ft_socket.bind((self._address[0], 0))
                port = ft_socket.getsockname()[1]
                conn.sendMsg(Message.JsonMsg(BuiltInOpCode.FT_TRANSFER_PORT, port=port))
                ft_socket.settimeout(self.__ft_timeout)
                ft_socket.listen(1)
                c_socket, c_addr = ft_socket.accept()
                return c_socket
            except OSError:
                return None

    def sendfile(self, conn: HTcpSocket, path: str, filename: str):
        c_socket = self._get_ft_transfer_conn(conn)
        if c_socket is None:
            return
        with c_socket:
            try:
                fin = open(path, 'rb')
            except OSError as e:  # file error
                print(e)
                return
            try:
                c_socket.sendFile(fin, filename)
            finally:
                fin.close()

    def recvfile(self, conn: HTcpSocket) -> str:
        c_socket = self._get_ft_transfer_conn(conn)
        if c_socket is None:
            return ""
        with c_socket:
            try:
                down_path = c_socket.recvFile()
            except OSError:
                return ""
        return down_path

    def sendfiles(self, conn: HTcpSocket, paths: list[str], filenames: list[str]) -> int:
        if len(paths) != len(filenames):
            return 0
        c_socket = self._get_ft_transfer_conn(conn)
        if c_socket is None:
            return 0
        count_sent = 0
        with c_socket:
            try:
                files_header_msg = Message.JsonMsg(BuiltInOpCode.FT_SEND_FILES_HEADER, {"file_count": len(paths)})
                c_socket.sendMsg(files_header_msg)
            except OSError:
                return 0
            for i in range(len(paths)):
                path = paths[i]
                filename = filenames[i]
                try:
                    fin = open(path, 'rb')
                except OSError as e:  # file error
                    print(e)
                    continue
                try:
                    c_socket.sendFile(fin, filename)
                    count_sent += 1
                except OSError:
                    return count_sent
                finally:
                    fin.close()
        return count_sent

    def recvfiles(self, conn: HTcpSocket) -> list[str]:
        c_socket = self._get_ft_transfer_conn(conn)
        if c_socket is None:
            return []
        down_path_list = []
        with c_socket:
            try:
                files_header_msg = c_socket.recvMsg()
            except (OSError, MessageError):
                return []
            file_count = files_header_msg.get("file_count")
            for i in range(file_count):
                try:
                    path = c_socket.recvFile()
                    if path:
                        down_path_list.append(path)
                except OSError:
                    break
        return down_path_list

    def setOnMsgRecvByOpCodeCallback(self, opcode: int, callback: OnMessageReceivedCallback):
        self.__onMsgRecvByOpCodeCallbackDict[opcode] = callback

    def popOnMsgRecvByOpCodeCallback(self, opcode: int):
        self.__onMsgRecvByOpCodeCallbackDict.pop(opcode)

    def setOnMessageReceivedCallback(self, callback: OnMessageReceivedCallback):
        self.__onMessageReceivedCallback = callback

    def setOnConnectedCallback(self, callback: OnConnectedCallback):
        self.__onConnectedCallback = callback

    def setOnDisconnectedCallback(self, callback: OnDisconnectedCallback):
        self.__onDisconnectedCallback = callback

    def _onMessageReceived(self, conn: HTcpSocket, msg: Message):
        opcode = msg.opcode()
        callback = self.__onMsgRecvByOpCodeCallbackDict.get(opcode)
        if callback is not None:
            finished = callback(conn, msg)
            if finished:
                return
        if self.__onMessageReceivedCallback:
            self.__onMessageReceivedCallback(conn, msg)

    def _onConnected(self, conn: HTcpSocket, addr):
        if self.__onConnectedCallback:
            self.__onConnectedCallback(conn, addr)

    def _onDisconnected(self, conn: HTcpSocket, addr):
        if self.__onDisconnectedCallback:
            self.__onDisconnectedCallback(conn, addr)


class HTcpSelectorServer(__HTcpServer):
    """以selector实现并发的HTcpServer"""

    class __HServerSelector:
        def __init__(self, hserver: "HTcpSelectorServer"):
            self.hserver: "HTcpSelectorServer" = hserver
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
            self.hserver._onConnected(conn, addr)

        def callback_read(self, conn: HTcpSocket):
            if not conn.isValid():
                # 主动关闭连接后会进入以下代码段
                print("not a socket")
                self.remove(conn)
                return
            addr = conn.getpeername()
            flag_error = False
            try:
                msg = conn.recvMsg()  # receive msg
            except OSError:
                flag_error = True
                print("connection error: {}".format(addr))
            except MessageError:
                flag_error = True
                print("message error: {}".format(addr))
            if flag_error:
                self.remove(conn)
                print("connection closed (read): {}".format(addr))
                self.hserver.closeconn(conn)
            else:
                self.msgs[conn] = msg
                self.selector.modify(conn, selectors.EVENT_WRITE, self.callback_write)

        def callback_write(self, conn: HTcpSocket):
            addr = conn.getpeername()
            msg = self.msgs[conn]
            if msg:
                self.hserver._onMessageReceived(conn, msg)
                self.msgs[conn] = None
            if conn.isValid():  # may be disconnected in messageHandle
                self.selector.modify(conn, selectors.EVENT_READ, self.callback_read)
            else:
                # 主动关闭连接后会进入以下代码段
                self.remove(conn)
                print("connection closed (write): {}".format(addr))
        
        def remove(self, conn: HTcpSocket):
            self.selector.unregister(conn)
            del self.msgs[conn]

    def __init__(self, addr):
        super().__init__(addr)
        self.__selector = self.__HServerSelector(self)

    def startserver(self):
        self.__selector.start(self._address)

    def closeserver(self):
        self.__selector.stop()

    def closeconn(self, conn: HTcpSocket):
        """主动关闭一个连接

        如果直接使用 conn.close() 则会导致不触发 onDisconnected 回调.
        """
        addr = conn.getpeername()
        conn.close()
        self._onDisconnected(conn, addr)


class HTcpThreadingServer(__HTcpServer):
    """以socketserver.ThreadingTCPServer实现并发的HTcpServer"""

    class __HRequestHandler(BaseRequestHandler):
        request: HTcpSocket
        client_address: tuple
        server: "HTcpThreadingServer.__HThreadingTCPServer"

        def __init__(self, request, client_address, server):
            super().__init__(request, client_address, server)

        def setup(self):
            print("connected: {}".format(self.client_address))
            self.server.hserver._onConnected(self.request, self.client_address)

        def handle(self):
            conn = self.request
            addr = self.client_address
            while True:
                try:
                    msg = conn.recvMsg()  # receive msg
                # except ConnectionResetError:
                #     print("connection reset: {}".format(addr))
                #     return
                except OSError:
                    print("connection error: {}".format(addr))
                    return
                except MessageError:  # message error
                    print("message error: {}".format(addr))
                    self.server.hserver.closeconn(conn)  # close connection
                    return
                else:
                    self.server.hserver._onMessageReceived(conn, msg)

        def finish(self):
            print("connection closed: {}".format(self.client_address))
            self.server.hserver._onDisconnected(self.request, self.client_address)

    class __HThreadingTCPServer(ThreadingTCPServer):
        def __init__(self, hserver: "HTcpThreadingServer", server_address, RequestHandlerClass):
            super().__init__(server_address, RequestHandlerClass, bind_and_activate=False)
            self.socket = HTcpSocket(self.address_family)
            self.hserver: "HTcpThreadingServer" = hserver

        def get_request(self):
            return self.socket.accept()

    def __init__(self, server_address):
        super().__init__(server_address)
        self.__server = self.__HThreadingTCPServer(self, server_address, self.__HRequestHandler)

    def startserver(self):
        try:
            self.__server.server_bind()
            self.__server.server_activate()
        except:
            self.__server.server_close()
            raise
        print("server start at {}".format(self.__server.server_address))
        self.__server.serve_forever()

    def closeserver(self):
        self.__server.shutdown()

    def closeconn(self, conn: HTcpSocket):
        self.__server.shutdown_request(conn)


class HUdpServer:
    OnMsgRecvByOpCodeCallback = Callable[[Message, Optional[tuple]], bool]  # 返回False时会继续进行OnMessageReceivedCallback
    OnMessageReceivedCallback = Callable[[Message, Optional[tuple]], None]

    def __init__(self, addr):
        self._address = addr
        self.__udp_socket = HUdpSocket()

        self.__onMsgRecvByOpCodeCallbackDict: dict[int, self.OnMsgRecvByOpCodeCallback] = {}
        self.__onMessageReceivedCallback: Optional[self.OnMessageReceivedCallback] = None

    def socket(self) -> HUdpSocket:
        return self.__udp_socket

    def startserver(self):
        self.__udp_socket.bind(self._address)
        while self.__udp_socket.isValid():
            try:
                msg, from_ = self.__udp_socket.recvMsg()
                self._onMessageReceived(msg, from_)
            except MessageError:
                continue

    def closeserver(self):
        self.__udp_socket.close()

    def sendto(self, msg: Message, c_addr):
        self.__udp_socket.sendMsg(msg, c_addr)

    def setOnMsgRecvByOpCodeCallback(self, opcode: int, callback: OnMessageReceivedCallback):
        self.__onMsgRecvByOpCodeCallbackDict[opcode] = callback

    def popOnMsgRecvByOpCodeCallback(self, opcode: int):
        self.__onMsgRecvByOpCodeCallbackDict.pop(opcode)

    def setOnMessageReceivedCallback(self, callback: OnMessageReceivedCallback):
        self.__onMessageReceivedCallback = callback

    def _onMessageReceived(self, msg: Message, c_addr: Optional[tuple]):
        opcode = msg.opcode()
        callback = self.__onMsgRecvByOpCodeCallbackDict.get(opcode)
        if callback is not None:
            finished = callback(msg, c_addr)
            if finished:
                return
        if self.__onMessageReceivedCallback:
            self.__onMessageReceivedCallback(msg, c_addr)
