# -*- coding: utf-8 -*-
import sys
sys.path.append("..")
from src.hsocket.hserver import HTcpThreadingServer
from src.hsocket.hsocket import HTcpSocket, Message
from traceback import print_exc
from threading import Thread
from time import sleep


def onMessageReceived(conn: HTcpSocket, msg: Message):
    addr = conn.getpeername()
    match msg.opcode():
        case 0:
            text = msg.get("text")
            print(addr, text)
            conn.sendMsg(Message.JsonMsg(0, 1, reply="hello 0"))
        case 1:
            text = msg.get("text")
            print(addr, text)
            conn.sendMsg(Message.JsonMsg(0, 1, reply="hello 1"))
        case 990:
            # 主动断开连接
            print("主动断开连接")
            server.closeconn(conn)
        case 991:
            # 新的线程中主动断开连接
            def disconnect_conn():
                sleep(2)
                print("新的线程中主动断开连接")
                server.closeconn(conn)
            th = Thread(target=disconnect_conn)
            th.start()
        case _:
            pass

def onDisconnected(conn: HTcpSocket, addr):
    print("onDisconnected")
        

if __name__ == '__main__':
    server = HTcpThreadingServer(("127.0.0.1", 40000))
    server.addOnMessageReceivedDo(onMessageReceived)
    server.addOnDisconnectedDo(onDisconnected)
    try:
        server.startserver()
    except Exception as e:
        print(print_exc())
    input("press enter to exit")
