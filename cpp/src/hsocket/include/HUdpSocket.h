#pragma once
#include "HSocket.h"
#include "Message.h"

class HUdpSocket : public HSocket
{
public:
	HUdpSocket();

	bool sendMsg(const Message &msg, const IPv4Address &addr);

	Message recvMsg(IPv4Address *addr);
};
