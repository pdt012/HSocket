# -*- coding: utf-8 -*-
import sys
sys.path.append("..")
from src.hsocket.server import HTcpServer
from src.hsocket.socket import HSocketTcp, Message
from traceback import print_exc


class FileServerApp(HTcpServer):
    def _messageHandle(self, conn: "HSocketTcp", msg: "Message"):
        addr = conn.getpeername()
        match msg.opcode():
            case 0:
                text = msg.get("text")
                print(addr, text)
                conn.sendMsg(Message.JsonMsg(0, 1, text="hello"))
            case 101:  # get file
                self.sendFile(conn, "files/test1.txt", "test1-from-server.txt")
            case 102:  # put file
                self.recvFile(conn, "downloads/")
            case _:
                pass
    def _onDisconnected(self, addr):
        return super()._onDisconnected(addr)
        

if __name__ == '__main__':
    server = FileServerApp()
    try:
        server.start(("127.0.0.1", 40000))
    except Exception as e:
        print(print_exc())
    input("press enter to exit")
