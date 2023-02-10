# -*- coding: utf-8 -*-
import sys
sys.path.append("..")
from src.hsocket.hserver import HUdpServer
from src.hsocket.hsocket import HUdpSocket, Message
from traceback import print_exc


class UdpServerApp(HUdpServer):
    def _messageHandle(self, msg: "Message", c_addr):
        match msg.opcode():
            case 0:
                text = msg.get("text")
                print(c_addr, text)
                self.sendto(Message.JsonMsg(0, 1, reply="hello 0"), c_addr)
            case 1:
                text = msg.get("text")
                print(c_addr, text)
                self.sendto(Message.JsonMsg(0, 1, reply="hello 1"), c_addr)
            case _:
                pass
        

if __name__ == '__main__':
    server = UdpServerApp()
    try:
        server.startserver(("127.0.0.1", 40000))
    except Exception as e:
        print(print_exc())
    input("press enter to exit")
