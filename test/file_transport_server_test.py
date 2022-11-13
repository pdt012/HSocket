# -*- coding: utf-8 -*-
import sys
sys.path.append("..")
from src.hsocket.server import HTcpServer
from src.hsocket.socket import FTP_PORT, HSocketTcp, Message
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
                filesock = conn.createFileTranCon(FTP_PORT)
                filesock.sendFile("files/test1.txt", "test1-from-server.txt")
            case 102:  # put file
                filesock = conn.createFileTranCon(FTP_PORT)
                filesock.recvFile("downloads/")
            case 201:  # get files
                filesock = conn.createFileTranCon(FTP_PORT)
                filesock.sendFiles(["files/test1.txt", "files/test2.txt"], 
                        ["test1-from-server.txt", "test2-from-server.txt"])
            case 202:  # put files
                filesock = conn.createFileTranCon(FTP_PORT)
                filesock.recvFiles("downloads/")
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
