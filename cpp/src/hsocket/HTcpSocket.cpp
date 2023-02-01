#include "pch.h"
#include "util.h"
#include "HTcpSocket.h"
#include "./include/convert/convert.h"
#include <fstream>

#define USE_UNICODE_FILEPATHS

namespace SocketConfig {
	int BUFFER_SIZE = 1024;
}

HTcpSocket::HTcpSocket()
	: HSocket(PF_INET, SOCK_STREAM, IPPROTO_TCP)
{
}

bool HTcpSocket::sendMsg(const Message &msg)
{
	sendall(msg.toString());
	return true;
}

Message HTcpSocket::recvMsg()
{
	std::string data;
	Header header;
	std::string headerdata = recv(HEADER_LENGTH);
	memcpy_s(&header, HEADER_LENGTH, headerdata.c_str(), HEADER_LENGTH);
	int size = header.length;
	while (data.size() < size) {  // 未接收完
		int recvSize = min(size - data.size(), SocketConfig::BUFFER_SIZE);
		std::string recvData = recv(recvSize);
		data += recvData;
	}
	if (!data.empty())
		return Message(header, data);
	else
		return Message(header, "");
}

bool HTcpSocket::sendFile(const std::string &path, const std::string &filename)
{
#ifdef USE_UNICODE_FILEPATHS
	std::wstring uniPath;
	gconvert::utf82uni(path, uniPath);
	if (!fileutil::exists(uniPath.c_str()))
		return false;
	int filesize = fileutil::size(uniPath.c_str());
#else
	if (!fileutil::exists(path.c_str()))
		return false;
	int filesize = fileutil::size(path.c_str());
#endif
	// 文件起始包
	neb::CJsonObject json;
	json.Add("filename", filename);
	json.Add("size", filesize);
	Message fileHeaderMsg = Message::JsonMsg(1001, 0, json);
	if (sendMsg(fileHeaderMsg)) {
#ifdef USE_UNICODE_FILEPATHS
		std::fstream fp(uniPath, std::ios::binary | std::ios::in);
#else
		std::fstream fp(path, std::ios::binary | std::ios::in);
#endif
		char *buf = new char[SocketConfig::BUFFER_SIZE];
		while (!fp.eof()) {
			fp.read(buf, SocketConfig::BUFFER_SIZE);
			int readSize = fp.gcount();
			sendall(std::string(buf, readSize));
		}
		fp.close();
		// 文件终止包
		/*Message fileEndingMsg = recvMsg();
		if (fileEndingMsg.isValid()) {
			std::string recvFilename;
			int recvSize;
			fileEndingMsg.json()->Get("filename", recvFilename);
			fileEndingMsg.json()->Get("size", recvSize);
			if (filename == recvFilename and filesize == recvSize)
				return true;
		}*/
		return true;
	}
	return false;
}

std::string HTcpSocket::recvFile()
{
	// 文件起始包
	Message fileHeaderMsg = recvMsg();
	if (fileHeaderMsg.isValid()) {
		std::string filename;
		int size;
		fileHeaderMsg.json()->Get("filename", filename);
		fileHeaderMsg.json()->Get("size", size);
		if (!filename.empty() && size > 0) {
			if (!fileutil::exists(SocketConfig::DEFAULT_DOWNLOAD_PATH))
				fileutil::mkdir(SocketConfig::DEFAULT_DOWNLOAD_PATH);
			std::string downPath = pathutil::join(SocketConfig::DEFAULT_DOWNLOAD_PATH, filename);
			int totalRecvSize = 0;  // 收到的字节数
#ifdef USE_UNICODE_FILEPATHS
			std::wstring uniDownPath;
			gconvert::utf82uni(downPath, uniDownPath);
			std::fstream fp(uniDownPath, std::ios::binary | std::ios::out);
#else
			std::fstream fp(downPath, std::ios::binary | std::ios::out);
#endif
			// todo: 异常处理
			while (totalRecvSize < size) {
				int recvSize = min(size - totalRecvSize, SocketConfig::BUFFER_SIZE);
				std::string data = recv(recvSize);
				fp.write(data.c_str(), data.size());
				totalRecvSize += data.size();
			}
			// 文件终止包
			/*neb::CJsonObject json;
			json.Add("filename", filename);
			json.Add("size", size);
			Message fileEndingMsg = Message::JsonMsg(1002, 0, json);
			if (sendMsg(fileEndingMsg))
				return downPath;*/
			return downPath;
		}
	}
	return "";
}

int HTcpSocket::sendFiles(std::vector<std::string> &pathlist, std::vector<std::string> &namelist)
{
	if (pathlist.size() != namelist.size())
		return 0;
	// 文件起始包
	neb::CJsonObject json;
	json.Add("count", pathlist.size());
	Message filesHeaderMsg = Message::JsonMsg(1011, 0, json);
	if (sendMsg(filesHeaderMsg)) {
		int countSuccess = 0;
		for (int i = 0; i < pathlist.size(); i++) {
			if (sendFile(pathlist[i], namelist[i]))
				countSuccess++;
		}
		return countSuccess;
	}
	return 0;
}

std::vector<std::string> HTcpSocket::recvFiles()
{
	// 文件起始包
	Message fileHeaderMsg = recvMsg();
	if (!fileHeaderMsg.isValid()) {
		return std::vector<std::string>();
	}
	int count;
	fileHeaderMsg.json()->Get("count", count);
	std::vector<std::string> pathlist;
	for (int i = 0; i < count; i++) {
		std::string downPath = recvFile();
		if (!downPath.empty())
			pathlist.push_back(downPath);
	}
	return pathlist;
}
