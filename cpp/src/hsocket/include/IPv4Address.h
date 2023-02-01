#pragma once
#include <string>
#include <WinSock2.h>

class IPv4Address
{
public:
	std::string ip;
	unsigned short port;
	IPv4Address() : ip(""), port(0) {};
	IPv4Address(const std::string &ip, unsigned short port) : ip(ip), port(port) {};
	/*生成 SOCKADDR 网络地址*/
	sockaddr_in to_sockaddr_in() const;
	static IPv4Address from_sockaddr(SOCKADDR sockaddr);
};


sockaddr_in v4addr_to_sockaddr(const std::string &ip, unsigned short port);


/*地址错误*/
class AddressError : public std::exception
{
public:
	AddressError() : message("<AddressError>") {}
	AddressError(std::string desc) : message("<AddressError>" + desc) {}
	virtual ~AddressError() = default;
	virtual const char *what() const throw () { return message.c_str(); }
private:
	std::string message;
};
