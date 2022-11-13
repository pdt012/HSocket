# -*- coding: utf-8 -*-
import sys
sys.path.append("..")
from src.hsocket.client import HTcpClient, ClientMode
from src.hsocket.socket import Message, FTP_PASV
from traceback import print_exc


ASYN = True


class FileClientApp(HTcpClient):
    def __init__(self):
        super().__init__(ClientMode.ASYNCHRONOUS if ASYN else ClientMode.SYNCHRONOUS)
    
    def _messageHandle(self, msg: "Message"):
        print(msg)

    def _onDisconnected(self):
        return super()._onDisconnected()


if ASYN:
    client = FileClientApp()
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
                match code:
                    case 0:
                        client.send(Message.JsonMsg(code, 0, text="test message send by client"))
                    case 101:  # get file
                        client.send(Message.HeaderOnlyMsg(code))
                        filesock = client.createFileTranCon(FTP_PASV)
                        if filesock:
                            filesock.recvFile("downloads/")
                    case 102:  # put file
                        client.send(Message.HeaderOnlyMsg(code))
                        filesock = client.createFileTranCon(FTP_PASV)
                        if filesock:
                            filesock.sendFile("files/test1.txt", "test1-from-client.txt")
                    case 201:  # get files
                        client.send(Message.HeaderOnlyMsg(code))
                        filesock = client.createFileTranCon(FTP_PASV)
                        if filesock:
                            filesock.recvFiles("downloads/")
                    case 202:  # put files
                        client.send(Message.HeaderOnlyMsg(code))
                        filesock = client.createFileTranCon(FTP_PASV)
                        if filesock:
                            filesock.sendFiles(["files/test1.txt", "files/test2.txt"], 
                                    ["test1-from-client.txt", "test2-from-client.txt"])
                    case _:
                        pass
            else:
                break
    except Exception as e:
        print(print_exc())
    input("press enter to exit")
else: 
    client = FileClientApp()
    client.connect(("127.0.0.1", 40000))
    print("start")
    try:
        while 1:
            code = input(">>>")
            if code.isdigit():
                code = int(code)
                response = None
                match code:
                    case 0:
                        response = client.request(Message.JsonMsg(code, 0, text="test message send by client"))
                        print(response)
                    case 101:  # get file
                        client.send(Message.HeaderOnlyMsg(code))
                        client._socket().recvFile("downloads/")
                    case 102:  # put file
                        client.send(Message.HeaderOnlyMsg(code))
                        client._socket().sendFile("files/test1.txt", "test1-from-client.txt")
                    case _:
                        pass
            else:
                break
    except Exception as e:
        print(print_exc())
    input("press enter to exit")
