# HSocket

- 兼容c++和python的协议；
- 支持纯文本/json的数据报协议;
- 基于该协议的tcp/udp通信api
- 对tcp协议下文件传输的简单封装。

## python端
- 基于selectors实现的并发tcp服务端类HTcpSelectorServer;
- 基于socketserver.ThreadingTCPServer实现的并发tcp服务端类HTcpThreadingServer;
- udp服务端类;
- 支持request-response模式/channel模式的tcp/udp客户端类。

## c++端
- 对winSock的封装；
- 支持request-response模式/channel模式的tcp/udp客户端类。
- 打包为lib供其他应用使用。
