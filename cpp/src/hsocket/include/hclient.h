#pragma once
#include <vector>
#include <thread>
#include <condition_variable>
#include "HTcpSocket.h"

enum BuiltInOpCode : unsigned short {
	FT_TRANSFER_PORT = 60020,  // 文件传输端口{ "port": port }
	FT_SEND_FILES_HEADER = 62000  // 多文件传输时头部信息{ "file_count": 文件数 }
};


enum ClientMode {
	SYNCHRONOUS,
	ASYNCHRONOUS
};


class HTcpClient abstract
{
private:
	HTcpSocket tcpSocket;
	ClientMode mode;
	std::string ftServerIp = "";
	int ftServerPort = 0;
	std::thread thMessage;
	std::mutex mtxFTPort;
	std::condition_variable conFTPort;

public:

	HTcpClient(ClientMode mode);

	HTcpSocket socket() {
		return tcpSocket;
	}

	void connect(IPv4Address addr);

	void close();

	bool isClosed() {
		return tcpSocket.isValid();
	}

	bool sendmsg(const Message &msg);

	Message request(const Message &msg);

	void sendfile(std::string path, std::string filename);

	std::string recvfile();

	int sendfiles(std::vector<std::string> paths, std::vector<std::string> filenames);

	std::vector<std::string> recvfiles();
private:
	bool getFTTransferPort();

	void recvHandle();
public:
	void messageHandle(const Message &msg) {};

	virtual void onDisconnect() abstract;
};
