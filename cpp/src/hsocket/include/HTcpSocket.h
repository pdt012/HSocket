#pragma once
#include "HSocket.h"
#include "Message.h"
#include <vector>

namespace SocketConfig {
	extern int BUFFER_SIZE;
	const char DEFAULT_DOWNLOAD_PATH[] = "download/";
}

class HTcpSocket : public HSocket
{
public:
	HTcpSocket();

	bool sendMsg(const Message &msg);

	Message recvMsg();

	bool sendFile(const std::string &path, const std::string &filename);

	std::string recvFile();

	int sendFiles(std::vector<std::string> &pathlist, std::vector<std::string> &namelist);

	std::vector<std::string> recvFiles();
};
