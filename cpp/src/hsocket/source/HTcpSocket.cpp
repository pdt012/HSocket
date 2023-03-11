#include "pch.h"
#include "util.h"
#include "HTcpSocket.h"
#include "convert/convert.h"
#include <fstream>
#include <iostream>

// true表示使用的字符串都是utf8编码, 否则都是默认系统编码
#define USING_UTF8_STRING false

HTcpSocket::HTcpSocket()
	: HSocket(PF_INET, SOCK_STREAM, IPPROTO_TCP)
{
}

void HTcpSocket::sendMsg(const Message &msg)
{
	sendall(msg.toBytes());
}

Message HTcpSocket::recvMsg()
{
	std::string data;
	Header header;
	std::string headerdata = recv(HEADER_LENGTH);
	memcpy_s(&header, HEADER_LENGTH, headerdata.c_str(), HEADER_LENGTH);
	int size = header.length;
	while (data.size() < size) {  // 未接收完
		int recvSize = min(size - data.size(), SocketConfig::recvBufferSize);
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
#if USING_UTF8_STRING
	this->sendall(filename);  // filename
#else
	std::string utf8Filename;
	gconvert::ansi2utf8(filename, utf8Filename);
	this->sendall(utf8Filename);  // filename
#endif
	this->sendall(std::string(1, '\0'));  //name end
	char filesize_b[4];
	memcpy_s(filesize_b, 4, &filesize, 4);
	this->sendall(std::string(filesize_b, 4));  // filesize
	// file content
	char *buf = new char[SocketConfig::fileBufferSize];
	while (!file.eof()) {
		file.read(buf, SocketConfig::fileBufferSize);
		int readSize = file.gcount();
		this->sendall(std::string(buf, readSize));
	}
}

std::string HTcpSocket::recvFile()
{
	// filename
	std::string filename;
	while (true) {
		std::string s;
		try {
			s = this->recv(1);
		}
		catch (SocketError e) {
			return "";
		}
		char c = s[0];
		if (c != '\0')
			filename += c;
		else
			break;
	}
	// filesize
	std::string filesize_b = this->recv(4);
	int filesize;
	memcpy_s(&filesize, 4, filesize_b.c_str(), 4);
	// file content
#if USING_UTF8_STRING
	std::string ansiDownloadDirectory;
	gconvert::utf82ansi(SocketConfig::downloadDirectory, ansiDownloadDirectory);
#else
	std::string ansiDownloadDirectory = SocketConfig::downloadDirectory;
	std::string ansiFilename;
	gconvert::utf82ansi(filename, ansiFilename);
#endif
	if (!filename.empty() && filesize > 0) {
		if (!fileutil::exists(ansiDownloadDirectory.c_str()))
			fileutil::mkdir(ansiDownloadDirectory.c_str());
		std::string downloadPath = pathutil::join(ansiDownloadDirectory, ansiFilename);
		int totalRecvSize = 0;  // 收到的字节数
		std::fstream fout(downloadPath, std::ios::binary | std::ios::out);
		if (fout.fail())
			return "";
		while (totalRecvSize < filesize) {
			int recvSize = min(filesize - totalRecvSize, SocketConfig::recvBufferSize);
			std::string data = recv(recvSize);
			fout.write(data.c_str(), data.size());
			totalRecvSize += data.size();
		}
		fout.close();
		return downloadPath;
	}
	return "";
}

void HTcpSocket::sendFiles(std::vector<std::string>& pathList, std::vector<std::string>& filenameList, std::vector<std::string>& succeedPathListOut)
{
	succeedPathListOut.clear();
	if (pathList.size() != filenameList.size())
		throw std::invalid_argument("Length of 'path_list' & 'filename_list' is not matched.");
	// files header
	int fileCount = pathList.size();
	char fileCount_b[4];
	memcpy_s(fileCount_b, 4, &fileCount, 4);
	this->sendall(std::string(fileCount_b, 4));  // file count
	// send files
	for (int i = 0; i < pathList.size(); i++) {
		std::string path = pathList[i];
		std::string filename = filenameList[i];
		std::ifstream fin(path, std::ios::binary | std::ios::in);
		if (fin.fail()) {
			std::cout << "File not found: " << "\"" << path << "\"" << std::endl;
			continue;
		}
		try {
			this->sendFile(fin, filename);
			succeedPathListOut.push_back(path);
			fin.close();
		}
		catch (SocketError e) {
			fin.close();
			throw e;
		}
	}
}

void HTcpSocket::recvFiles(std::vector<std::string>& downloadPathListOut)
{
	downloadPathListOut.clear();
	// files header
	std::string fileCount_b = this->recv(4);
	int fileCount;
	memcpy_s(&fileCount, 4, fileCount_b.c_str(), 4);
	// recv files
	for (int i = 0; i < fileCount; i++) {
		std::string path = this->recvFile();
		if (!path.empty())
			downloadPathListOut.push_back(path);
	}
}
