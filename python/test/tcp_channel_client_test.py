# -*- coding: utf-8 -*-
import sys
sys.path.append("..")
from src.hsocket.hclient import HTcpChannelClient
from src.hsocket.hsocket import Message
from traceback import print_exc


def onMessageReceived(msg: "Message"):
    print(msg)


if __name__ == '__main__':
    client = HTcpChannelClient()
    client.setOnMessageReceivedCallback(onMessageReceived)
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
                client.sendmsg(Message.JsonMsg(code, text=f"test message<{code}> send by client"))
            else:
                break
    except Exception as e:
        print(print_exc())
    input("press enter to exit")

