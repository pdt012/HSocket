#pragma once
#include <vector>
#include <map>
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

	void setOnConnectedCallback(void (*callback)()) {
		this->onConnectedCallback = callback;
	}

	void setOnDisconnectedCallback(void (*callback)()) {
		this->onDisconnectedCallback = callback;
	}

protected:
	virtual bool getFTTransferPort() = 0;

protected:
	void onConnected() {
		if (onConnectedCallback)
			onConnectedCallback();
	}

	void onDisconnected() {
		if (onDisconnectedCallback)
			onDisconnectedCallback();
	}

private:
	void (*onConnectedCallback)() = nullptr;
	void (*onDisconnectedCallback)() = nullptr;
};


class HTcpChannelClient : public HTcpClient
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

	void setOnMsgRecvByOpCodeCallback(ushort opcode, bool (*callback)(Message& msg)) {
		this->onMsgRecvByOpCodeCallbackMap.insert({ opcode, callback });
	}

	void popOnMsgRecvByOpCodeCallback(ushort opcode) {
		this->onMsgRecvByOpCodeCallbackMap.erase(opcode);
	}

	void setOnMessageReceivedCallback(void (*callback)(Message& msg)) {
		this->onMessageReceivedCallback = callback;
	}

private:
	void messageHandle();

protected:
	bool getFTTransferPort() override;

	void onMessageReceived(Message &msg);

private:
	void (*onMessageReceivedCallback)(Message& msg) = nullptr;
	std::map<ushort, bool (*)(Message& msg)> onMsgRecvByOpCodeCallbackMap;
};


class HTcpReqResClient : public HTcpClient
{
public:
	HTcpReqResClient();

	bool sendmsg(const Message &msg) override;

	Message request(const Message &msg);

protected:
	bool getFTTransferPort() override;
};
