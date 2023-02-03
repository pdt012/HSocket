#include "pch.h"
#include "hclient.h"
#include <fstream>

HTcpClient::HTcpClient()
{
	tcpSocket.setblocking(true);
}

void HTcpClient::connect(IPv4Address addr)
{
	tcpSocket.connect(addr.ip.c_str(), addr.port);
	ftServerIp = addr.ip;
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
	ftSocket.connect(ftServerIp.c_str(), ftServerPort);
	std::ifstream fin(path, std::ios::binary | std::ios::in);
	ftSocket.sendFile(fin, filename);
	fin.close();
	ftSocket.close();
}

std::string HTcpClient::recvfile()
{
	if (!this->getFTTransferPort())
		return "";
	// recv
	HTcpSocket ftSocket;
	ftSocket.connect(ftServerIp.c_str(), ftServerPort);
	std::string downPath = ftSocket.recvFile();
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
	ftSocket.connect(ftServerIp.c_str(), ftServerPort);
	neb::CJsonObject json;
	json.Add("file_count", paths.size());
	Message filesHeaderMsg = Message::JsonMsg(BuiltInOpCode::FT_SEND_FILES_HEADER, 0, json);
	ftSocket.sendMsg(filesHeaderMsg);
	for (int i = 0; i < paths.size(); i++) {
		std::string path = paths[i];
		std::string filename = filenames[i];
		std::ifstream fin(path, std::ios::binary | std::ios::in);
		ftSocket.sendFile(fin, filename);
		countSent++;
		fin.close();
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
	ftSocket.connect(ftServerIp.c_str(), ftServerPort);
	Message filesHeaderMsg = ftSocket.recvMsg();
	int fileCount = filesHeaderMsg.getInt("file_count");
	for (int i = 0; i < fileCount; i++) {
		std::string path = ftSocket.recvFile();
		if (!path.empty())
			downPathList.push_back(path);
	}
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
	}
}

bool HTcpChannelClient::getFTTransferPort()
{
	try {
		std::unique_lock<std::mutex> ulock(mtxFTPort);
		conFTPort.wait(ulock);
		return true;
	}
	catch (SocketError e) {
		return false;
	}
	return false;
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

Message HTcpReqResClient::request(const Message &msg)
{
	if (this->sendmsg(msg)) {
		try {
			Message response = tcpSocket.recvMsg();
			return response;
		}
		catch (SocketError e) {
			this->onDisconnected();
			this->close();
			return Message(ContentType::ERROR_);
		}
	}
	return Message(ContentType::ERROR_);
}

bool HTcpReqResClient::getFTTransferPort()
{
	try {
		Message msg = tcpSocket.recvMsg();
		if (msg.opcode() == BuiltInOpCode::FT_TRANSFER_PORT) {
			ftServerPort = msg.getInt("port");
			return true;
		}
	}
	catch (SocketError e) {
		return false;
	}
	return false;
}
