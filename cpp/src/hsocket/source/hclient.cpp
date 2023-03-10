#include "pch.h"
#include "hclient.h"
#include <fstream>
#include <iostream>

HTcpClient::HTcpClient()
{
	tcpSocket.setblocking(true);
}

void HTcpClient::connect(IPv4Address addr)
{
	tcpSocket.connect(addr.ip.c_str(), addr.port);
	ftServerIp = addr.ip;
	this->onConnected();
}

void HTcpClient::close()
{
	tcpSocket.close();
}

void HTcpClient::sendfile(std::string path, std::string filename)
{
	if (!this->getFTTransferPort())
		return;
	// send
	HTcpSocket ftSocket;
	try {
		ftSocket.connect(ftServerIp.c_str(), ftServerPort);
	}
	catch (SocketError e) {
		ftSocket.close();
		return;
	}
	std::ifstream fin = std::ifstream(path, std::ios::binary | std::ios::in);
	if (fin.fail()) {
		std::cout << "File not found: " << "\"" << path << "\"" << std::endl;
		return;
	}
	try {
		ftSocket.sendFile(fin, filename);
	}
	catch (SocketError e) {}
	fin.close();
	ftSocket.close();
}

std::string HTcpClient::recvfile()
{
	if (!this->getFTTransferPort())
		return "";
	// recv
	HTcpSocket ftSocket;
	std::string downPath = "";
	try {
		ftSocket.connect(ftServerIp.c_str(), ftServerPort);
		downPath = ftSocket.recvFile();
	}
	catch (SocketError e) {}
	ftSocket.close();
	return downPath;
}

int HTcpClient::sendfiles(std::vector<std::string> paths, std::vector<std::string> filenames)
{
	if (!this->getFTTransferPort())
		return 0;
	if (paths.size() != filenames.size())
		return 0;
	// send
	int countSent = 0;
	HTcpSocket ftSocket;
	try {
		ftSocket.connect(ftServerIp.c_str(), ftServerPort);
		neb::CJsonObject json;
		json.Add("file_count", paths.size());
		Message filesHeaderMsg = Message::JsonMsg(BuiltInOpCode::FT_SEND_FILES_HEADER, json);
		ftSocket.sendMsg(filesHeaderMsg);
	}
	catch (SocketError e) {
		ftSocket.close();
		return countSent;
	}
	for (int i = 0; i < paths.size(); i++) {
		std::string path = paths[i];
		std::string filename = filenames[i];
		std::ifstream fin(path, std::ios::binary | std::ios::in);
		if (fin.fail()) {
			std::cout << "File not found: " << "\"" << path << "\"" << std::endl;
			continue;
		}
		try {
			ftSocket.sendFile(fin, filename);
			countSent++;
			fin.close();
		}
		catch (SocketError e) {
			fin.close();
			break;
		}
	}
	ftSocket.close();
	return countSent;
}

std::vector<std::string> HTcpClient::recvfiles()
{
	if (!this->getFTTransferPort())
		return std::vector<std::string>();
	// recv
	std::vector<std::string> downPathList;
	HTcpSocket ftSocket;
	try {
		ftSocket.connect(ftServerIp.c_str(), ftServerPort);
		Message filesHeaderMsg = ftSocket.recvMsg();
		int fileCount = filesHeaderMsg.getInt("file_count");
		for (int i = 0; i < fileCount; i++) {
			try {
				std::string path = ftSocket.recvFile();
				if (!path.empty())
					downPathList.push_back(path);
			}
			catch (SocketError e) {
				break;
			}
		}
	}
	catch (SocketError e) {}
	catch (MessageError e) {}
	ftSocket.close();
	return downPathList;
}


HTcpChannelClient::HTcpChannelClient()
	: HTcpClient()
{
}

void HTcpChannelClient::connect(IPv4Address addr)
{
	HTcpClient::connect(addr);
	thMessage = std::thread(&HTcpChannelClient::messageHandle, this);
}

bool HTcpChannelClient::sendmsg(const Message &msg)
{
	try {
		tcpSocket.sendMsg(msg);
	}
	catch (SocketError e) {
		thMessage.join();  // make sure that 'onDisconnected' only runs once
		if (!isClosed()) {
			this->onDisconnected();
			this->close();
		}
		return false;
	}
	return true;
}

void HTcpChannelClient::messageHandle()
{
	while (!this->isClosed()) {
		try {
			Message msg = tcpSocket.recvMsg();
			if (msg.opcode() == BuiltInOpCode::FT_TRANSFER_PORT) {
				ftServerPort = msg.getInt("port");
				conFTPort.notify_one();
				continue;
			}
			this->onMessageReceived(msg);
		}
		catch (SocketError e) {
			if (e.getErrcode() == EAGAIN || e.getErrcode() == EWOULDBLOCK) {
				continue;
			}
			this->onDisconnected();
			this->close();
			break;
		}
		catch (MessageError e) {
			this->onDisconnected();
			this->close();
			break;
		}
	}
}

bool HTcpChannelClient::getFTTransferPort()
{
	std::unique_lock<std::mutex> ulock(mtxFTPort);
	std::cv_status status = conFTPort.wait_for(ulock, std::chrono::milliseconds(ftTimeout));
	if (status == std::cv_status::no_timeout)
		return true;
	else
		return false;
}

void HTcpChannelClient::onMessageReceived(Message& msg)
{
	ushort opcode = msg.opcode();
	auto iter = onMsgRecvByOpCodeCallbackMap.find(opcode);
	if (iter != onMsgRecvByOpCodeCallbackMap.end()) {
		bool finished = iter->second(msg);
		if (finished)
			return;
	}
	if (onMessageReceivedCallback)
		onMessageReceivedCallback(msg);
}


HTcpReqResClient::HTcpReqResClient()
	: HTcpClient()
{
}

bool HTcpReqResClient::sendmsg(const Message &msg)
{
	try {
		tcpSocket.sendMsg(msg);
	}
	catch (SocketError e) {
		if (!isClosed()) {
			this->onDisconnected();
			this->close();
		}
		return false;
	}
	return true;
}

std::optional<Message> HTcpReqResClient::request(const Message &msg)
{
	if (this->sendmsg(msg)) {
		bool flagError = false;
		try {
			Message response = tcpSocket.recvMsg();
			return response;
		}
		catch (SocketError e) {
			flagError = true;
		}
		catch (MessageError e) {
			flagError = true;  // 收到空包文时断开
		}
		if (flagError) {
			this->onDisconnected();
			this->close();
			return std::nullopt;
		}
	}
	return std::nullopt;
}

bool HTcpReqResClient::getFTTransferPort()
{
	try {
		Message msg = tcpSocket.recvMsg();
		if (msg.opcode() == BuiltInOpCode::FT_TRANSFER_PORT) {
			ftServerPort = msg.getInt("port");
			return true;
		}
		else
			return false;
	}
	catch (SocketError e) {
		return false;
	}
	catch (MessageError e) {
		return false;
	}
}
