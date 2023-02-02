#include "pch.h"
#include "HUdpSocket.h"

HUdpSocket::HUdpSocket()
	: HSocket(PF_INET, SOCK_DGRAM, IPPROTO_UDP)
{
}

bool HUdpSocket::sendMsg(const Message &msg, const IPv4Address &addr)
{
	std::string data = msg.toString();
	return sendto(data, addr) == data.size();
}

Message HUdpSocket::recvMsg(IPv4Address *addr)
{
	Message msg = Message::fromString(recvfrom(addr));
	return msg;
}
