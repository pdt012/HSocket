# -*- coding: utf-8 -*-
import sys
sys.path.append("..")
from src.hsocket.client import HAsynTcpClient
from src.hsocket.socket import Message
from traceback import print_exc


class AsynTcpClientApp(HAsynTcpClient):
    def __init__(self, addr):
        super().__init__(addr)

    def _messageHandle(self, msg: "Message"):
        print(msg)

    def _onDisconnected(self):
        return super()._onDisconnected()


if __name__ == '__main__':
    client = AsynTcpClientApp(("127.0.0.1", 40000))
    client.connect()
    print("start")
    try:
        while 1:
            if client.isclosed():
                print("client is closed")
                break
            code = input(">>>")
            if code.isdigit():
                code = int(code)
                match code:
                    case 0:
                        client.send(Message.JsonMsg(code, 0, text0="<0>test message send by client"))
                    case 1:
                        client.send(Message.JsonMsg(code, 0, text1="<1>test message send by client"))
                    case _:
                        pass
            else:
                break
    except Exception as e:
        print(print_exc())
    input("press enter to exit")

