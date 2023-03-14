# -*- coding: utf-8 -*-
import sys

sys.path.append("..")
from src.hsocket.hserver import HTcpSelectorServer
from src.hsocket.hsocket import HTcpSocket, Message
from traceback import print_exc
from threading import Thread
from time import sleep


def onRecv990(conn: HTcpSocket, msg: Message) -> bool:
    # 主动断开连接
    print("主动断开连接")
    server.closeconn(conn)
    return True


def onRecv991(conn: HTcpSocket, msg: Message) -> bool:
    # 新的线程中主动断开连接
    def disconnect_conn():
        sleep(2)
        print("新的线程中主动断开连接")
        server.closeconn(conn)

    th = Thread(target=disconnect_conn)
    th.start()
    return True


def onMessageReceived(conn: HTcpSocket, msg: Message):
    addr = conn.getpeername()
    match msg.opcode():
        case 0:
            text = msg.get("text")
            print(addr, text)
            conn.sendMsg(Message.JsonMsg(0, reply="hello 0"))
        case 1:
            text = msg.get("text")
            print(addr, text)
            conn.sendMsg(Message.JsonMsg(0, reply="hello 1"))
        case _:
            pass


def onDisconnected(conn: HTcpSocket, addr):
    print("onDisconnected")


if __name__ == '__main__':
    server = HTcpSelectorServer(("127.0.0.1", 40000))
    server.setOnMsgRecvByOpCodeCallback(990, onRecv990)
    server.setOnMsgRecvByOpCodeCallback(991, onRecv991)
    server.setOnMessageReceivedCallback(onMessageReceived)
    server.setOnDisconnectedCallback(onDisconnected)
    try:
        server.startserver()
    except Exception as e:
        print(print_exc())
    input("press enter to exit")
