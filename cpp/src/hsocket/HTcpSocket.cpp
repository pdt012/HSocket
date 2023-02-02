#include "pch.h"
#include "util.h"
#include "HTcpSocket.h"
#include "./include/convert/convert.h"
#include <fstream>

#define USE_UNICODE_FILEPATHS

namespace SocketConfig {
	int RECV_BUFFER_SIZE = 1024;
	int FILE_BUFFER_SIZE = 2048;
}

HTcpSocket::HTcpSocket()
	: HSocket(PF_INET, SOCK_STREAM, IPPROTO_TCP)
{
}

void HTcpSocket::sendMsg(const Message &msg)
{
	sendall(msg.toString());
}

Message HTcpSocket::recvMsg()
{
	std::string data;
	Header header;
	std::string headerdata = recv(HEADER_LENGTH);
	memcpy_s(&header, HEADER_LENGTH, headerdata.c_str(), HEADER_LENGTH);
	int size = header.length;
	while (data.size() < size) {  // 未接收完
		int recvSize = min(size - data.size(), SocketConfig::RECV_BUFFER_SIZE);
		std::string recvData = recv(recvSize);
		data += recvData;
	}
	if (!data.empty())
		return Message(header, data);
	else
		return Message(header, "");
}

void HTcpSocket::sendFile(std::ifstream &file, const std::string &filename)
{
	// get file size
	file.seekg(0, std::ios::end);
	unsigned int filesize = file.tellg();
	file.clear();
	file.seekg(0, std::ios::beg);
	// file header
	this->sendall(filename);  // filename
	this->sendall(std::string(1, '\0'));  //name end
	char filesize_b[4];
	memcpy_s(filesize_b, 4, &filesize, 4);
	this->sendall(std::string(filesize_b, 4));  // filesize
	// file content
	char *buf = new char[SocketConfig::FILE_BUFFER_SIZE];
	while (!file.eof()) {
		file.read(buf, SocketConfig::FILE_BUFFER_SIZE);
		int readSize = file.gcount();
		this->sendall(std::string(buf, readSize));
	}
}

std::string HTcpSocket::recvFile()
{
	// filename
	std::string filename;
	while (true) {
		std::string s = this->recv(1);
		char c = s[0];
		if (c != '\0')
			filename += c;
		else
			break;
	}
	// filesize
	std::string filesize_b = this->recv(4);
	unsigned int filesize;
	memcpy_s(&filesize, 4, filesize_b.c_str(), 4);
	// file content
	if (!filename.empty() && filesize > 0) {
		if (!fileutil::exists(SocketConfig::DEFAULT_DOWNLOAD_PATH))
			fileutil::mkdir(SocketConfig::DEFAULT_DOWNLOAD_PATH);
		std::string downPath = pathutil::join(SocketConfig::DEFAULT_DOWNLOAD_PATH, filename);
		int totalRecvSize = 0;  // 收到的字节数
#ifdef USE_UNICODE_FILEPATHS
		std::wstring uniDownPath;
		gconvert::utf82uni(downPath, uniDownPath);
		std::fstream fout(uniDownPath, std::ios::binary | std::ios::out);
#else
		std::fstream fp(downPath, std::ios::binary | std::ios::out);
#endif
		while (totalRecvSize < filesize) {
			int recvSize = min(filesize - totalRecvSize, SocketConfig::RECV_BUFFER_SIZE);
			std::string data = recv(recvSize);
			fout.write(data.c_str(), data.size());
			totalRecvSize += data.size();
		}
		fout.close();
		return downPath;
	}
	return "";
}
