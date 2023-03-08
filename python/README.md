# HSocket - Python

## 安装

1. 安装python，至少3.10 (www.python.org).
2. 进入 HSocket/python路径.
3. 运行 `python setup.py install .` 将hsocket安装到site-packages.

## 代码示例

运行server：

```py
# server.py
server = HTcpSelectorServer(("127.0.0.1", 40000))
server.startserver()
```

运行client:

```py
# client.py
client = HTcpReqResClient()
client.connect(("127.0.0.1", 40000))
```

先后执行以上两个代码文件即可看到连接成功的输出。

client发送消息：

```py
client = HTcpReqResClient()
client.connect(("127.0.0.1", 40000))
response = client.request(Message.PlainTextMsg(100, "hello, server!"))
print(response)
```

server添加消息回调：

```py
def onRecv_100(conn: HTcpSocket, msg: Message) -> bool:
    print(conn.getpeername())
    print(msg)
    conn.sendMsg(Message.PlainTextMsg(100, "hello, client!"))
    return True

server = HTcpSelectorServer(("127.0.0.1", 40000))
server.setOnMsgRecvByOpCodeCallback(1, onRecv_100)
server.startserver()
```
