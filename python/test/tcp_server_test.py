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
            case 0:
                text = msg.get("text0")
                print(addr, text)
                conn.sendMsg(Message.JsonMsg(0, 1, reply="hello 0"))
            case 1:
                text = msg.get("text1")
                print(addr, text)
                conn.sendMsg(Message.JsonMsg(0, 1, reply="hello 1"))
            case _:
                pass
    def _onDisconnected(self, addr):
        return super()._onDisconnected(addr)
        

if __name__ == '__main__':
    server = TcpServerApp()
    try:
        server.startserver(("127.0.0.1", 40000))
    except Exception as e:
        print(print_exc())
    input("press enter to exit")
