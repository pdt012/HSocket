# -*- coding: utf-8 -*-
import sys
sys.path.append("..")
from src.hsocket.hclient import HTcpChannelClient
from src.hsocket.hsocket import Message
from traceback import print_exc


class AsynTcpClientApp(HTcpChannelClient):
    def __init__(self):
        super().__init__()

    def _onMessageReceived(self, msg: "Message"):
        print(msg)

    def _onDisconnected(self):
        return super()._onDisconnected()


if __name__ == '__main__':
    client = AsynTcpClientApp()
    client.connect(("127.0.0.1", 40000))
    print("start")
    try:
        while 1:
            if client.isclosed():
                print("client is closed")
                break
            code = input(">>>")
            if code.isdigit():
                code = int(code)
                client.sendmsg(Message.JsonMsg(code, 0, text=f"test message<{code}> send by client"))
            else:
                break
    except Exception as e:
        print(print_exc())
    input("press enter to exit")

