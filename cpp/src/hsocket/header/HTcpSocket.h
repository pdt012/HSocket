#pragma once
#include "HSocket.h"
#include "message.h"

typedef SOCKET SOCKET;

class SocketConfig {
public:
	static inline int RECV_BUFFER_SIZE = 1024;
	static inline int FILE_BUFFER_SIZE = 2048;
	static inline std::string DEFAULT_DOWNLOAD_PATH = "download/";
};

class HTcpSocket : public HSocket
{
public:
	HTcpSocket();

	/**
	 * @throw SocketError 连接异常时抛出
	*/
	HTcpSocket accept() {
		return HTcpSocket(HSocket::accept());
	}

	/**
	 * @brief 发送一个数据包
	 * @param msg 发送的报文
	 * @throw SocketError 连接异常时抛出
	*/
	void sendMsg(const Message &msg);

	/**
	 * @brief 尝试接收一个数据包
	 * @throw SocketError 连接异常时抛出
     * @throw EmptyMessageError: 收到空报文时抛出
     * @throw MessageHeaderError: 报头解析异常时抛出
	 * @return 收到的报文
	*/
	Message recvMsg();

	/**
	 * @brief 发送一个文件
	 * @param path
	 * @param filename
	 * @throw SocketError 连接异常时抛出
	*/
	void sendFile(std::ifstream &file, const std::string &filename);

	/**
	 * @brief 尝试接收一个文件
	 * @throw SocketError 连接异常时抛出
	 * @return 成功接收的文件路径，若接收失败则返回空字符串
	*/
	std::string recvFile();

protected:
	HTcpSocket(SOCKET sock) :HSocket(sock) {}

};
