# -*- coding: utf-8 -*-
import sys
sys.path.append("..")
from src.hsocket.hserver import HTcpServer
from src.hsocket.hsocket import HTcpSocket, Message
from traceback import print_exc
from threading import Thread
from time import sleep


class TcpServerApp(HTcpServer):
    def _messageHandle(self, conn: "HTcpSocket", msg: "Message"):
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
                self.closeconn(conn)
            case 991:
                # 新的线程中主动断开连接
                def disconnect_conn():
                    sleep(2)
                    print("新的线程中主动断开连接")
                    self.closeconn(conn)
                th = Thread(target=disconnect_conn)
                th.start()
            case _:
                pass
    
    def _onDisconnected(self, conn, addr):
        print("_onDisconnected")
        return super()._onDisconnected(conn, addr)
        

if __name__ == '__main__':
    server = TcpServerApp()
    try:
        server.startserver(("127.0.0.1", 40000))
    except Exception as e:
        print(print_exc())
    input("press enter to exit")
