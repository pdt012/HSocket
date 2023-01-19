# -*- coding: utf-8 -*-
import sys
sys.path.append("..")
from src.hsocket.client import HUdpClient, ClientMode
from src.hsocket.socket import Message
from traceback import print_exc


class SynUdpClientApp(HUdpClient):
    def __init__(self, addr):
        super().__init__(addr, ClientMode.SYNCHRONOUS)


if __name__ == '__main__':
    client = SynUdpClientApp(("127.0.0.1", 40000))
    client.settimeout(5.0)
    print("start")
    try:
        while 1:
            code = input(">>>")
            if code.isdigit():
                code = int(code)
                match code:
                    case 0:
                        response = client.request(Message.JsonMsg(code, 0, text0="<0>test message send by client"))
                    case 1:
                        response = client.request(Message.JsonMsg(code, 0, text1="<1>test message send by client"))
                    case _:
                        continue
                print(response)
            else:
                break
    except Exception as e:
        print(print_exc())
    input("press enter to exit")

