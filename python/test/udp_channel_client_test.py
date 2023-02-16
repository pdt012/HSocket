# -*- coding: utf-8 -*-
import sys
sys.path.append("..")
from src.hsocket.hclient import HUdpChannelClient
from src.hsocket.hsocket import Message
from traceback import print_exc


def onMessageReceived(msg: "Message"):
    print('msg: ', msg)


if __name__ == '__main__':
    client = HUdpChannelClient(("127.0.0.1", 40000))
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

