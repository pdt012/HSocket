#pragma once
#include <vector>
#include <thread>
#include <condition_variable>
#include "HTcpSocket.h"

enum BuiltInOpCode : unsigned short {
	FT_TRANSFER_PORT = 60020,  // 文件传输端口{ "port": port }
	FT_SEND_FILES_HEADER = 62000  // 多文件传输时头部信息{ "file_count": 文件数 }
};


class HTcpClient abstract
{
protected:
	HTcpSocket tcpSocket;
	std::string ftServerIp = "";
	int ftServerPort = 0;

public:
	HTcpClient();

	HTcpSocket socket() {
		return tcpSocket;
	}

	virtual void connect(IPv4Address addr);

	virtual void close();

	virtual bool isClosed() {
		return !tcpSocket.isValid();
	}

	virtual bool sendmsg(const Message &msg) = 0;

	void sendfile(std::string path, std::string filename);

	std::string recvfile();

	int sendfiles(std::vector<std::string> paths, std::vector<std::string> filenames);

	std::vector<std::string> recvfiles();

protected:
	virtual bool getFTTransferPort() = 0;

protected:
	virtual void onDisconnected() abstract;
};


class HTcpChannelClient abstract : public HTcpClient
{
private:
	std::thread thMessage;
	std::mutex mtxFTPort;
	std::condition_variable conFTPort;
	int ftTimeout = 15;

public:
	HTcpChannelClient();

	void connect(IPv4Address addr) override;

	bool sendmsg(const Message &msg) override;

    void setFTTimeout(int sec) {
        ftTimeout = sec;
	}

private:
	void messageHandle();

protected:
	bool getFTTransferPort() override;

	virtual void onMessageReceived(Message &msg) abstract;
};


class HTcpReqResClient abstract : public HTcpClient
{
public:
	HTcpReqResClient();

	bool sendmsg(const Message &msg) override;

	Message request(const Message &msg);

protected:
	bool getFTTransferPort() override;
};
