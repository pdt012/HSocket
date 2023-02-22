# -*- coding: utf-8 -*-
import sys
sys.path.append("..")
from src.hsocket.p2pclient import HTcpP2PClient
from src.hsocket.hsocket import Message
from traceback import print_exc


class TcpP2PClientApp(HTcpP2PClient):
    def __init__(self):
        super().__init__()

    def _messageHandle(self, msg: "Message"):
        print('msg: ',msg)


if __name__ == '__main__':
    client = TcpP2PClientApp()
    op = input("choose mode: 0- passive | 1- active >>>")
    if op == "0":
        sock_port = input("input sock port: ")
        sock_port = int(sock_port)
        client.bind(("127.0.0.1", sock_port))
        print(f"start at {client.getsockaddr()}")
        client.wait()
    elif op =="1":
        peer_port = input("input peer port: ")
        peer_port = int(peer_port)
        client.connect(("127.0.0.1", peer_port))
    else:
        raise ValueError(f"invalid input: '{op}'")
    try:
        while 1:
            code = input(">>>")
            if code.isdigit():
                code = int(code)
                response = None
                match code:
                    case 0:
                        response = client.send(Message.JsonMsg(code, text0="<0>test message send by peer"))
                    case 1:
                        response = client.send(Message.JsonMsg(code, text1="<1>test message send by peer"))
                    case _:
                        pass
                print(response)
            else:
                break
    except Exception as e:
        print(print_exc())
    input("press enter to exit")
