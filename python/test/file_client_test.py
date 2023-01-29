# -*- coding: utf-8 -*-
import sys
sys.path.append("..")
from src.hsocket.hclient import HTcpClient, ClientMode
from src.hsocket.hsocket import Message
from traceback import print_exc


class SynTcpClientApp(HTcpClient):
    def __init__(self):
        super().__init__(ClientMode.SYNCHRONOUS)

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
                response = None
                match code:
                    case 100:  # 上传
                        client.sendmsg(Message.HeaderOnlyMsg(100))
                        client.sendfile("testfile/test1.txt", "test1_by_client.txt")
                        print(f"send file")
                    case 101:  # 下载
                        client.sendmsg(Message.HeaderOnlyMsg(101))
                        path = client.recvfile()
                        print(f"recv file '{path}'")
                    case 110:  # 上传
                        client.sendmsg(Message.HeaderOnlyMsg(110))
                        count = client.sendfiles(["testfile/test1.txt", "testfile/test2.txt"],
                                                 ["test1_by_client.txt", "test2_by_client.txt"])
                        print(f"send files ({count})")
                    case 111:  # 下载
                        client.sendmsg(Message.HeaderOnlyMsg(111))
                        paths = client.recvfiles()
                        print(f"recv file {paths}")
                    case _:
                        pass
                print(response)
            else:
                break
    except Exception as e:
        print(print_exc())
    input("press enter to exit")

