# -*- coding: utf-8 -*-
import sys
sys.path.append("..")
from src.hsocket.hclient import HUdpReqResClient
from src.hsocket.hsocket import Message
from traceback import print_exc


if __name__ == '__main__':
    client = HUdpReqResClient(("127.0.0.1", 40000))
    client.settimeout(5.0)
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

