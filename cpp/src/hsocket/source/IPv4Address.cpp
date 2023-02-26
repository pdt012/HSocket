#include "pch.h"
#include "IPv4Address.h"
#include <WS2tcpip.h>
#include <fstream>

sockaddr_in IPv4Address::to_sockaddr_in() const
{
	return v4addr_to_sockaddr(this->ip, this->port);
}

IPv4Address IPv4Address::from_sockaddr(SOCKADDR sockaddr)
{
	char ip_buf[16];
	sockaddr_in *sin = (sockaddr_in *)&sockaddr;
	if (inet_ntop(PF_INET, &sin->sin_addr.s_addr, ip_buf, 16) == NULL)
		throw AddressError();
	return IPv4Address(ip_buf, ntohs(sin->sin_port));
}


sockaddr_in v4addr_to_sockaddr(const std::string &ip, unsigned short port)
{
	sockaddr_in sin;
	memset(&sin, 0, sizeof(sin));  // 0填充
	sin.sin_family = PF_INET;  // IPv4
	if (inet_pton(PF_INET, ip.c_str(), &sin.sin_addr.s_addr) != 1)  // IP地址
		throw AddressError(ip);
	sin.sin_port = htons(port);  // 端口
	return sin;
}
