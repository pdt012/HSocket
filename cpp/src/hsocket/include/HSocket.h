#pragma once
#include "IPv4Address.h"
#include <WinSock2.h>
#pragma comment (lib, "ws2_32.lib")

class ConnectionError : public std::exception
{
public:
	ConnectionError() {
		errcode = WSAGetLastError();
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
	virtual ~ConnectionError() = default;
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

#define THROW_IF_SOCKET_ERROR(code) if (code == SOCKET_ERROR) throw ConnectionError();

class HSocket
{
public:
	HSocket(int af, int type, int protocol) {
		//创建套接字
		WSADATA wsaData;
		int errcode = WSAStartup(MAKEWORD(2, 2), &wsaData);
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

	int setsockopt(int level, int optname, const char *optval, int optlen) {
		int ret = ::setsockopt(handle, level, optname, optval, optlen);
		THROW_IF_SOCKET_ERROR(ret);
		return ret;
	}

	int getsockopt(int level, int optname, char *optval, int *optlen) {
		int ret = ::getsockopt(handle, level, optname, optval, optlen);
		THROW_IF_SOCKET_ERROR(ret);
		return ret;
	}

	IPv4Address getsockname() {
		SOCKADDR name;
		int namelen = 0;
		int ret = ::getsockname(handle, &name, &namelen);
		THROW_IF_SOCKET_ERROR(ret);
		return IPv4Address::from_sockaddr(name);
	}

	IPv4Address getpeername() {
		SOCKADDR name;
		int namelen = 0;
		int ret = ::getpeername(handle, &name, &namelen);
		THROW_IF_SOCKET_ERROR(ret);
		return IPv4Address::from_sockaddr(name);
	}

	void bind(const char *ip, unsigned short port) {
		sockaddr_in saddr = v4addr_to_sockaddr(ip, port);
		int ret = ::bind(handle, (SOCKADDR *)&saddr, sizeof(SOCKADDR));
		THROW_IF_SOCKET_ERROR(ret);
	}

	void connect(const char *ip, unsigned short port) {
		sockaddr_in saddr = v4addr_to_sockaddr(ip, port);
		int ret = ::connect(handle, (SOCKADDR *)&saddr, sizeof(SOCKADDR));
		THROW_IF_SOCKET_ERROR(ret);
	}

	void listen(SOCKET sock, int backlog) {
		int ret = ::listen(sock, backlog);
		THROW_IF_SOCKET_ERROR(ret);
	}

	HSocket accept() {
		SOCKADDR clientAddr;
		int size = sizeof(SOCKADDR);
		SOCKET clientSock = ::accept(handle, (SOCKADDR *)&clientAddr, &size);
		if (clientSock == INVALID_SOCKET)
			throw ConnectionError();
		else
			return HSocket(clientSock);
	}

	int sendall(const std::string &data) {
		int sentSize = 0;
		do {
			int ret = ::send(handle, data.c_str(), data.size(), NULL);
			THROW_IF_SOCKET_ERROR(ret);
			sentSize += ret;
		} while (sentSize < data.size());  // 没发完
		return sentSize;
	}

	std::string recv(int buflen) {
		char *buf = new char[buflen];
		int ret = ::recv(handle, buf, buflen, NULL);
		if (ret == SOCKET_ERROR) {
			delete[] buf;
			throw ConnectionError();
		}
		else if (ret == 0) {
			delete[] buf;
			throw ConnectionError();
		}
		else {
			std::string str = std::string(buf, ret);
			delete[] buf;
			return str;
		}
	}

	int sendto(const std::string &data, const IPv4Address &addr) {
		sockaddr_in to = addr.to_sockaddr_in();
		int ret = ::sendto(handle, data.c_str(), data.size(), NULL, (SOCKADDR *)&to, sizeof(to));
		THROW_IF_SOCKET_ERROR(ret);
		return ret;
	}

	std::string recvfrom(IPv4Address *addr) {
		SOCKADDR from;
		int fromlen = sizeof(SOCKADDR);
		char *buf = new char[65535];
		int ret = ::recvfrom(handle, buf, 65535, NULL, &from, &fromlen);
		if (ret == SOCKET_ERROR) {
			delete[] buf;
			throw ConnectionError();
		}
		else if (ret == 0) {
			delete[] buf;
			throw ConnectionError();
		}
		else {
			addr->from_sockaddr(from);
			std::string str = std::string(buf, ret);
			delete[] buf;
			return str;
		}
	}

	int shutdown(int how) {
		int ret = ::shutdown(handle, how);
		THROW_IF_SOCKET_ERROR(ret);
		return ret;
	}

	int close() {
		int ret = ::closesocket(handle);
		THROW_IF_SOCKET_ERROR(ret);
		handle = NULL;
		return ret;
	}

private:
	HSocket(SOCKET sock) {
		this->handle = sock;
	}

private:
	SOCKET handle = NULL;
};
