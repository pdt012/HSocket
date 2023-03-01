#pragma once
#include <string>
#include <sstream>
#include "../include/CJsonObject/CJsonObject.hpp"

#define HEADER_LENGTH 8

typedef unsigned short ushort; 


/*Base class of message error.*/
class MessageError : public std::exception {};

/*Received an empty message.*/
class EmptyMessageError : public MessageError {};

/*Error in loading a message header.*/
class MessageHeaderError : public MessageError {};


enum ContentType : ushort
{
	HEADERONLY = 0x1,  // 只含报头
	PLAINTEXT = 0x2,  // 纯文本内容
	JSONOBJRCT = 0x3,  // JSON对象
	BINARY = 0x4,  // 二进制串
};


inline std::string getContentTpeName(ContentType contenttype) {
	switch (contenttype)
	{
	case HEADERONLY:
		return "HEADERONLY";
	case PLAINTEXT:
		return "PLAINTEXT";
	case JSONOBJRCT:
		return "JSONOBJRCT";
	case BINARY:
		return "BINARY";
	default:
		return "";
	}
}


#pragma pack(2)
struct Header
{
	ContentType contenttype;  // 报文内容码
	ushort opcode;  // 操作码
	int length;  // 报文长度
};
#pragma pack()


class Message
{
private:
	ContentType __contenttype;  // 报文内容码
	ushort __opcode;  // 操作码
	std::string __content;
	neb::CJsonObject *__json = nullptr;

public:
	Message(ContentType contenttype, ushort opcode = 0, const std::string &content = "")
		: __contenttype(contenttype), __opcode(opcode), __content(content)
	{
		if (!content.empty()) {

			if (contenttype == ContentType::HEADERONLY)
				;
			else if (contenttype == ContentType::PLAINTEXT) {
				this->__content = content;
			}
			else if (contenttype == ContentType::JSONOBJRCT) {
				this->__content = content;
				this->__json = new neb::CJsonObject(content);
			}
		}
	}

	Message(const Message &msg)
		: __contenttype(msg.__contenttype), __opcode(msg.__opcode), __content(msg.__content)
	{
		this->__json = new neb::CJsonObject(msg.__json);
	}

	~Message() {
		delete __json;
	}

	/*由Header和正文内容组成Message*/
	Message(Header &header, const std::string &content)
		: Message(header.contenttype, header.opcode, content)
	{
	}

	/*不含正文的Message*/
	static Message HeaderOnlyMsg(ushort opcode = 0) {
		return Message(ContentType::HEADERONLY, opcode);
	}

	/*正文为纯文本的Message*/
	static Message PlainTextMsg(ushort opcode = 0, const std::string &text = "") {
		return Message(ContentType::PLAINTEXT, opcode, text);
	}

	/*正文为json对象的Message*/
	static Message JsonMsg(ushort opcode, neb::CJsonObject &json) {
		Message msg = Message(ContentType::JSONOBJRCT, opcode);
		msg.__json = new neb::CJsonObject(json);
		return msg;
	}

	/*获取内容码*/
	ContentType contenttype() {
		return this->__contenttype;
	}

	/*获取操作码*/
	ushort opcode() {
		return this->__opcode;
	}

	/*直接获取正文*/
	std::string content() {
		return this->__content;
	}

	neb::CJsonObject *json() {
		return this->__json;
	}

	int getInt(const std::string &key) {
		int value;
		__json->Get(key, value);
		return value;
	}

	float getFloat(const std::string &key) {
		float value;
		__json->Get(key, value);
		return value;
	}

	bool getBool(const std::string &key) {
		bool value;
		__json->Get(key, value);
		return value;
	}

	std::string getStr(const std::string &key) {
		std::string value;
		__json->Get(key, value);
		return value;
	}

	std::string toBytes() const {
		std::string cont;
		if (__contenttype == ContentType::HEADERONLY)
			cont = "";
		else if (__contenttype == ContentType::PLAINTEXT)
			cont = __content;
		else if (__contenttype == ContentType::JSONOBJRCT)
			cont = __json->ToString();
		else
			cont = __content;
		int length = cont.size();  // 数据包长度(不包含报头)
		Header header = Header{ __contenttype, __opcode, length };
		char buf[HEADER_LENGTH];
		memcpy_s(buf, sizeof(buf), &header, HEADER_LENGTH);
		return std::string(buf, HEADER_LENGTH) + cont;
	}

	/**
	 * @brief 二进制流转换为Message
	 * @param data 
	 * @throw EmptyMessageError 收到空报文时抛出
     * @throw MessageHeaderError 报头解析异常时抛出
	 * @return Message
	*/
	static Message fromBytes(const std::string &data) {
		if (data.empty())
			throw EmptyMessageError();
		if (data.size() != HEADER_LENGTH)
			throw MessageHeaderError();
		Header header;
		memcpy_s(&header, HEADER_LENGTH, data.c_str(), HEADER_LENGTH);
		return Message(header, data.substr(HEADER_LENGTH));
	}

	std::string toString() const {
		std::stringstream sstream;
		sstream << "<Message>" << "(" << getContentTpeName(__contenttype) << ") " << "opcode: " << __opcode << "\n"
			<< "content:\n" << __content;
		return sstream.str();
	}

};
