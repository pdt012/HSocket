# -*- coding: utf-8 -*-
import sys

sys.path.append("..")
from src.server import HTcpServer
from src.socket import HTcpSocket, Message
from traceback import print_exc


class TcpServerApp(HTcpServer):
    def _messageHandle(self, conn: "HTcpSocket", msg: "Message"):
        addr = conn.getpeername()
        match msg.opcode():
            case 100:  # 上传
                conn.recvFile()
            case 101:  # 下载
                conn.sendFile("testfile/test1.txt", "test1_by_server.txt")
            case 110:  # 上传
                conn.recvFiles()
            case 111:  # 下载
                conn.sendFiles(["testfile/test1.txt", "testfile/test2.txt"],
                               ["test1_by_server.txt", "test2_by_server.txt"])
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
