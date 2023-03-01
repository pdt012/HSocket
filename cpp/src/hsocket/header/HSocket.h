#pragma once
#include "ipaddress.h"
#include <WinSock2.h>
#pragma comment (lib, "ws2_32.lib")

class SocketError : public std::exception
{
public:
	SocketError(int errcode)
		: errcode(errcode)
	{
		char msgBuf[256];
		::FormatMessageA(
			FORMAT_MESSAGE_ALLOCATE_BUFFER | FORMAT_MESSAGE_FROM_SYSTEM,
			NULL,
			errcode,
			0,
			msgBuf,
			sizeof(msgBuf),
			NULL);
		message = std::string(msgBuf);
	}
	SocketError() : SocketError(WSAGetLastError()) {}
	virtual ~SocketError() = default;
	virtual const char *what() const noexcept {
		return message.c_str();
	}
	int getErrcode() {
		return errcode;
	}
private:
	int errcode;
	std::string message;
};

#define THROW_IF_SOCKET_ERROR(code) if (code == SOCKET_ERROR) throw SocketError();

class HSocket
{
public:
	HSocket(int af, int type, int protocol) {
		//创建套接字
		WSADATA wsaData;
		int errcode = WSAStartup(MAKEWORD(2, 2), &wsaData);
		if (errcode != 0)
			throw SocketError(errcode);
		this->handle = socket(af, type, protocol);
	}

	~HSocket() {
		this->close();
		int ret = WSACleanup();
		if (ret == SOCKET_ERROR)
			int errcode = GetLastError();
	}

	SOCKET fileno() {
		return this->handle;
	}

	bool isValid() {
		return handle != -1;
	}

	/**
	 * @throw SocketError 连接异常时抛出
	*/
	void settimeout(int msec) {
		int timeout = msec;
		this->setsockopt(SOL_SOCKET, SO_SNDTIMEO, (char *)&timeout, sizeof(int));
		this->setsockopt(SOL_SOCKET, SO_RCVTIMEO, (char *)&timeout, sizeof(int));
	}

	/**
	 * @throw SocketError 连接异常时抛出
	*/
	void setblocking(bool blocking) {
		u_long arg = !blocking;
		int ret = ioctlsocket(handle, FIONBIO, &arg);
		THROW_IF_SOCKET_ERROR(ret);
	}

	/**
	 * @throw SocketError 连接异常时抛出
	*/
	void setsockopt(int level, int optname, const char *optval, int optlen) {
		int ret = ::setsockopt(handle, level, optname, optval, optlen);
		THROW_IF_SOCKET_ERROR(ret);
	}

	/**
	 * @throw SocketError 连接异常时抛出
	*/
	void getsockopt(int level, int optname, char *optval, int *optlen) {
		int ret = ::getsockopt(handle, level, optname, optval, optlen);
		THROW_IF_SOCKET_ERROR(ret);
	}

	/**
	 * @throw SocketError 连接异常时抛出
	*/
	IPv4Address getsockname() {
		SOCKADDR name;
		int namelen = 0;
		int ret = ::getsockname(handle, &name, &namelen);
		THROW_IF_SOCKET_ERROR(ret);
		return IPv4Address::from_sockaddr(name);
	}

	/**
	 * @throw SocketError 连接异常时抛出
	*/
	IPv4Address getpeername() {
		SOCKADDR name;
		int namelen = 0;
		int ret = ::getpeername(handle, &name, &namelen);
		THROW_IF_SOCKET_ERROR(ret);
		return IPv4Address::from_sockaddr(name);
	}

	/**
	 * @throw SocketError 连接异常时抛出
	*/
	void bind(const char *ip, unsigned short port) {
		sockaddr_in saddr = IPv4Address::to_sockaddr_in(ip, port);
		int ret = ::bind(handle, (SOCKADDR *)&saddr, sizeof(SOCKADDR));
		THROW_IF_SOCKET_ERROR(ret);
	}

	/**
	 * @throw SocketError 连接异常时抛出
	*/
	void connect(const char *ip, unsigned short port) {
		sockaddr_in saddr = IPv4Address::to_sockaddr_in(ip, port);
		int ret = ::connect(handle, (SOCKADDR *)&saddr, sizeof(SOCKADDR));
		THROW_IF_SOCKET_ERROR(ret);
	}

	/**
	 * @throw SocketError 连接异常时抛出
	*/
	void listen(int backlog) {
		int ret = ::listen(handle, backlog);
		THROW_IF_SOCKET_ERROR(ret);
	}

	/**
	 * @throw SocketError 连接异常时抛出
	*/
	SOCKET accept() {
		SOCKADDR clientAddr;
		int size = sizeof(SOCKADDR);
		SOCKET clientSock = ::accept(handle, (SOCKADDR *)&clientAddr, &size);
		if (clientSock == INVALID_SOCKET)
			throw SocketError();
		else
			return clientSock;
	}

	/**
	 * @brief
	 * @param data
	 * @throw SocketError 连接异常时抛出
	 * @return 发送长度
	*/
	int sendall(const std::string &data) {
		int sentSize = 0;
		do {
			int ret = ::send(handle, data.c_str(), data.size(), NULL);
			THROW_IF_SOCKET_ERROR(ret);
			sentSize += ret;
		} while (sentSize < data.size());  // 没发完
		return sentSize;
	}

	/**
	 * @brief
	 * @param buflen
	 * @throw SocketError 连接异常时抛出
	 * @return 接收的内容
	*/
	std::string recv(int buflen) {
		char *buf = new char[buflen];
		int ret = ::recv(handle, buf, buflen, NULL);
		if (ret == -1) {
			delete[] buf;
			throw SocketError();
		}
		else if (ret == 0) {
			delete[] buf;
			throw SocketError();
		}
		else {
			std::string str = std::string(buf, ret);
			delete[] buf;
			return str;
		}
	}

	/**
	 * @brief
	 * @param data
	 * @param addr
	 * @throw SocketError 连接异常时抛出
	 * @return 发送长度
	*/
	int sendto(const std::string &data, const IPv4Address &addr) {
		sockaddr_in to = addr.to_sockaddr_in();
		int ret = ::sendto(handle, data.c_str(), data.size(), NULL, (SOCKADDR *)&to, sizeof(to));
		THROW_IF_SOCKET_ERROR(ret);
		return ret;
	}

	/**
	 * @brief
	 * @param addr 返回发送者地址
	 * @throw SocketError 连接异常时抛出
	 * @return 接收的内容
	*/
	std::string recvfrom(IPv4Address *addr) {
		SOCKADDR from;
		int fromlen = sizeof(SOCKADDR);
		char *buf = new char[65535];
		int ret = ::recvfrom(handle, buf, 65535, NULL, &from, &fromlen);
		if (ret == SOCKET_ERROR) {
			delete[] buf;
			throw SocketError();
		}
		else if (ret == 0) {
			delete[] buf;
			throw SocketError();
		}
		else {
			addr->from_sockaddr(from);
			std::string str = std::string(buf, ret);
			delete[] buf;
			return str;
		}
	}

	/**
	 * @throw SocketError 连接异常时抛出
	*/
	void shutdown(int how) {
		int ret = ::shutdown(handle, how);
		THROW_IF_SOCKET_ERROR(ret);
	}

	/**
	 * @throw SocketError 连接异常时抛出
	*/
	void close() {
		if (!this->isValid())
			return;
		int ret = ::closesocket(handle);
		THROW_IF_SOCKET_ERROR(ret);
		handle = -1;
	}

protected:
	HSocket(SOCKET sock) {
		this->handle = sock;
	}

protected:
	SOCKET handle = NULL;
};
