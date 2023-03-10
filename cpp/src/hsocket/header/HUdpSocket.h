#pragma once
#include "HSocket.h"
#include "message.h"

class HUdpSocket : public HSocket
{
public:
	HUdpSocket();

	/**
	 * @brief 发送一个数据包
	 * @param msg 发送的报文
	 * @param addr 目标地址
	 * @return 数据是否全部发送
	*/
	bool sendMsg(const Message &msg, const IPv4Address &addr);

	/**
	 * @brief 接收一个数据包
	 * @param addr 返回发送方地址
     * @throw EmptyMessageError: 收到空报文时抛出
     * @throw MessageHeaderError: 报头解析异常时抛出
	 * @return 数据包(可能为Error包或空包)
	*/
	Message recvMsg(IPv4Address *addr);
};
