# -*- coding: utf-8 -*-
import sys
sys.path.append("..")
from src.hsocket.hclient import HUdpChannelClient
from src.hsocket.hsocket import Message
from traceback import print_exc


class AsynUdpClientApp(HUdpChannelClient):
    def __init__(self, addr):
        super().__init__(addr)

    def _onMessageReceived(self, msg: "Message"):
        print('msg: ',msg)


if __name__ == '__main__':
    client = AsynUdpClientApp(("127.0.0.1", 40000))
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
                        client.sendmsg(Message.JsonMsg(code, 0, text0="<0>test message send by client"))
                    case 1:
                        client.sendmsg(Message.JsonMsg(code, 0, text1="<1>test message send by client"))
                    case _:
                        pass
            else:
                break
    except Exception as e:
        print(print_exc())
    input("press enter to exit")
