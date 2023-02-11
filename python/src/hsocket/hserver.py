# -*- coding: utf-8 -*-
import selectors
from socketserver import ThreadingTCPServer, BaseRequestHandler
from abc import abstractmethod
from .hsocket import *
from .message import *


class BuiltInOpCode(IntEnum):
    FT_TRANSFER_PORT = 60020  # 文件传输端口 {"port": port}
    FT_SEND_FILES_HEADER = 62000  # 多文件传输时头部信息 {"file_count": 文件数}


class __HTcpServer:
    def __init__(self, addr):
        self._address: str = addr
        self.__ft_timeout = 15

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

    def _get_ft_transfer_conn(self, conn: HTcpSocket) -> HTcpSocket:
        with HTcpSocket() as ft_socket:
            ft_socket.bind((self._address[0], 0))
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
                print(1111)
                down_path = c_socket.recvFile()
                print(down_path)
                print(2222)
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
    def onMessageReceived(self, conn: HTcpSocket, msg: Message):
        ...

    def onConnected(self, conn: HTcpSocket, addr):
        pass

    def onDisconnected(self, conn: HTcpSocket, addr):
        pass


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
            self.hserver.onConnected(conn, addr)

        def callback_read(self, conn: HTcpSocket):
            if not conn.isValid():
                # 主动关闭连接后会进入以下代码段
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
                print("connection closed (read): {}".format(addr))
                self.hserver.onDisconnected(conn, addr)  # disconnect callback

        def callback_write(self, conn: HTcpSocket):
            addr = conn.getpeername()
            msg = self.msgs[conn]
            if msg:
                self.hserver.onMessageReceived(conn, msg)
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
        self.onDisconnected(conn, addr)


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
            self.server.hserver.onConnected(self.request, self.client_address)

        def handle(self):
            conn = self.request
            addr = self.client_address
            while True:
                try:
                    msg = conn.recvMsg()  # receive msg
                except ConnectionResetError:
                    print("connection reset: {}".format(addr))
                    msg = None
                except OSError:  # socket is closed
                    print("socket is closed")
                    return 
                if msg and msg.isValid():
                    self.server.hserver.onMessageReceived(conn, msg)
                else:  # empty msg or error
                    break

        def finish(self):
            print("connection closed: {}".format(self.client_address))
            self.server.hserver.onDisconnected(self.request, self.client_address)

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
    def __init__(self, addr):
        self._address = addr
        self.__udp_socket = HUdpSocket()

    def socket(self) -> HUdpSocket:
        return self.__udp_socket

    def startserver(self):
        self.__udp_socket.bind(self._address)
        while self.__udp_socket.isValid():
            msg, from_ = self.__udp_socket.recvMsg()
            self.onMessageReceived(msg, from_)

    def closeserver(self):
        self.__udp_socket.close()

    def sendto(self, msg: Message, c_addr):
        self.__udp_socket.sendMsg(msg, c_addr)

    @abstractmethod
    def onMessageReceived(self, msg: Message, c_addr):
        ...
