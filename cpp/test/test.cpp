#include <iostream>
#include "../src/hsocket/header/hclient.h"
#include "../src/hsocket/include/convert/convert.cpp"

#ifdef _DEBUG
#ifdef _WIN64
#pragma comment(lib,"../x64/Debug/hsocketd.lib")
#else
#pragma comment(lib,"../Debug/hsocketd.lib")
#endif
#else
#ifdef _WIN64
#pragma comment(lib,"../x64/Release/hsocket.lib")
#else
#pragma comment(lib,"../Release/hsocket.lib")
#endif
#endif



int main()
{
	try {
		HTcpReqResClient client;
		client.connect(IPv4Address("127.0.0.1", 40000));
		std::cout << "start" << std::endl;
		while (true) {
			int code = -1;
			std::cout << ">>>";
			std::cin >> code;
			if (std::cin.fail()) break;
			switch (code)
			{
			case 100:
				client.sendmsg(Message::HeaderOnlyMsg(100));
				client.sendfile("testfile/test1.txt", "test1_by_cpp_client.txt");
				std::cout << "send file" << std::endl;
				break;
			case 101: {
				client.sendmsg(Message::HeaderOnlyMsg(101));
				std::string path = client.recvfile();
				std::cout << "recv file" << "'" << path << "'" << std::endl; }
				break;
			case 110: {
				client.sendmsg(Message::HeaderOnlyMsg(110));
				std::vector<std::string> pathlist = { "testfile/test1.txt", "testfile/test2.txt" };
				std::vector<std::string> namelist = { "test1_by_cpp_client.txt", "test2_by_cpp_client.txt" };
				int count = client.sendfiles(pathlist, namelist);
				std::cout << "send files" << "(" << count << ")" << std::endl; }
					break;
			case 111: {
				client.sendmsg(Message::HeaderOnlyMsg(111));
				std::vector<std::string> paths = client.recvfiles();
				std::cout << "recv files" << "[";
				for (std::string path : paths) {
					std::cout << "'" << path << "', ";
				}
				std::cout << "]" << std::endl; }
				break;
			default: {
				neb::CJsonObject json;
				std::stringstream sstream;
				sstream << "test message<" << code << "> send by c++ client";
				json.Add("text", sstream.str());
				Message msg = Message::JsonMsg(code, json);
				std::optional<Message> replyMsg = client.request(msg);
				if (replyMsg.has_value()) {
					std::cout << replyMsg->toString() << std::endl;
				}}
				  break;
			}
		}
	}
	catch (SocketError e) {
		std::cout << "error" << e.getErrcode() << "  " << e.what() << std::endl;
		return 0;
	}
}
