#pragma once
#include <vector>
#include <map>
#include <optional>
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

	HTcpSocket &socket() {
		return tcpSocket;
	}

	virtual void connect(IPv4Address addr);

	virtual void close();

	virtual bool isClosed() {
		return !tcpSocket.isValid();
	}

	/**
	 * @brief 向服务端发送报文
	 * @param msg 发送的报文
	 * @return 是否成功
	*/
	virtual bool sendmsg(const Message &msg) = 0;

	/**
	 * @brief 发送一个文件
	 * @param path 文件路径
	 * @param filename 文件名
	*/
	void sendfile(std::string path, std::string filename);

	/**
	 * @brief 接收一个文件
	 * @return 下载的文件路径，失败时返回空字符串
	*/
	std::string recvfile();

	/**
	 * @brief 发送多个文件
	 * @param paths 文件路径列表
	 * @param filenames 文件名列表
	 * @return 成功发送的文件数
	*/
	int sendfiles(std::vector<std::string> paths, std::vector<std::string> filenames);

	/**
	 * @brief 接收多个文件
	 * @return 下载的文件路径列表
	*/
	std::vector<std::string> recvfiles();

	/**
	 * @brief 设置连接到服务端时的回调
	 * @param callback 回调方法
	*/
	void setOnConnectedCallback(void (*callback)()) {
		this->onConnectedCallback = callback;
	}

	/**
	 * @brief 设置连接断开时的回调
	 * @param callback 回调方法
	*/
	void setOnDisconnectedCallback(void (*callback)()) {
		this->onDisconnectedCallback = callback;
	}

protected:
	/**
	 * @brief 获取服务端的文件传输端口
	 * @return 是否成功获取
	*/
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

    /**
     * @brief 设置文件传输的超时时长
     * @param sec 
    */
    void setFTTimeout(int sec) {
        ftTimeout = sec;
	}

	/**
	 * @brief 设置收到指定操作码报文时的回调
	 * @param opcode 操作码
	 * @param callback 回调方法
	*/
	void setOnMsgRecvByOpCodeCallback(ushort opcode, bool (*callback)(Message& msg)) {
		this->onMsgRecvByOpCodeCallbackMap.insert({ opcode, callback });
	}

	/**
	 * @brief 取消收到指定操作码报文时的回调
	 * @param opcode 操作码
	*/
	void popOnMsgRecvByOpCodeCallback(ushort opcode) {
		this->onMsgRecvByOpCodeCallbackMap.erase(opcode);
	}

	/**
	 * @brief 设置收到报文时的回调(调用晚于`setOnMsgRecvByOpCodeCallback`设置的回调)
	 * @param callback 回调方法
	*/
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

	/**
	 * @brief 发送一个请求报文，接收一个响应报文
	 * @param msg 发送的报文
	 * @return 接收到的响应报文，失败时返回null
	*/
	std::optional<Message> request(const Message& msg);

protected:
	bool getFTTransferPort() override;
};
