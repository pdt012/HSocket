# -*- coding: utf-8 -*-
import sys
sys.path.append("..")
from src.hsocket.hclient import HTcpReqResClient
from src.hsocket.hsocket import Message
from traceback import print_exc


class SynTcpClientApp(HTcpReqResClient):
    def __init__(self):
        super().__init__()

    def _onDisconnected(self):
        return super()._onDisconnected()


if __name__ == '__main__':
    client = SynTcpClientApp()
    client.connect(("127.0.0.1", 40000))
    print("start")
    try:
        while 1:
            code = input(">>>")
            if code.isdigit():
                code = int(code)
                response = client.request(Message.JsonMsg(code, 0, text=f"test message<{code}> send by client"))
                print(response)
            else:
                break
    except Exception as e:
        print(print_exc())
    input("press enter to exit")

