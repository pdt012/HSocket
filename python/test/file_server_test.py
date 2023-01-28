# -*- coding: utf-8 -*-
import sys

sys.path.append("..")
from src.hsocket.hserver import HTcpServer
from src.hsocket.hsocket import HTcpSocket, Message
from traceback import print_exc


class TcpServerApp(HTcpServer):
    def _messageHandle(self, conn: "HTcpSocket", msg: "Message"):
        addr = conn.getpeername()
        match msg.opcode():
            case 100:  # 上传
                path = self.recvfile(conn)
                print(f"recv file '{path}'")
            case 101:  # 下载
                self.sendfile(conn, "testfile/test1.txt", "test1_by_server.txt")
                print(f"send file")
            case 110:  # 上传
                paths = self.recvfiles(conn)
                print(f"recv file {paths}")
            case 111:  # 下载
                count = self.sendfiles(conn, ["testfile/test1.txt", "testfile/test2.txt"],
                                       ["test1_by_server.txt", "test2_by_server.txt"])
                print(f"send files ({count})")
            case _:
                pass

    def _onDisconnected(self, addr):
        return super()._onDisconnected(addr)


if __name__ == '__main__':
    server = TcpServerApp()
    try:
        server.start(("127.0.0.1", 40000))
    except Exception as e:
        print(print_exc())
    input("press enter to exit")
