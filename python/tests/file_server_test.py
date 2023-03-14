# -*- coding: utf-8 -*-
import sys

sys.path.append("..")
from src.hsocket.hserver import HTcpSelectorServer
from src.hsocket.hsocket import HTcpSocket, Message
from traceback import print_exc


def onMessageReceived(conn: HTcpSocket, msg: Message):
    match msg.opcode():
        case 100:  # 上传
            path = server.recvfile(conn)
            print(f"recv file '{path}'")
        case 101:  # 下载
            server.sendfile(conn, "testfile/test1.txt", "test1_by_server.txt")
            print(f"send file")
        case 110:  # 上传
            paths = server.recvfiles(conn)
            print(f"recv files {paths}")
        case 111:  # 下载
            paths = server.sendfiles(conn, ["testfile/test1.txt", "testfile/test2.txt"],
                                     ["test1_by_server.txt", "test2_by_server.txt"])
            print(f"send files {paths}")
        case _:
            pass


if __name__ == '__main__':
    server = HTcpSelectorServer(("127.0.0.1", 40000))
    server.setOnMessageReceivedCallback(onMessageReceived)
    try:
        server.startserver()
    except Exception as e:
        print(print_exc())
    input("press enter to exit")
