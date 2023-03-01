#pragma once
#include "HSocket.h"
#include "message.h"

typedef SOCKET SOCKET;

namespace SocketConfig {
	extern int RECV_BUFFER_SIZE;
	extern int FILE_BUFFER_SIZE;
	const char DEFAULT_DOWNLOAD_PATH[] = "download/";
}

class HTcpSocket : public HSocket
{
public:
	HTcpSocket();

	HTcpSocket accept() {
		return HTcpSocket(HSocket::accept());
	}

	/**
	 * @brief 发送一个数据包
	 * @param msg
	 * @throw SocketError 连接异常时抛出
	*/
	void sendMsg(const Message &msg);

	/**
	 * @brief 尝试接收一个数据包
	 * @throw SocketError 连接异常时抛出
	 * @return 收到空报文时返回空Message
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
