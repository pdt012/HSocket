#pragma once
#include <string>
#include "./CJsonObject/CJsonObject.hpp"

#define HEADER_LENGTH 10

enum ContentType : short
{
	NONE = 0x0,  // 空报文
	ERROR_ = 0x1,  // 错误报文
	HEADERONLY = 0x2,  // 只含报头
	PLAINTEXT = 0x3,  // 纯文本内容
	JSONOBJRCT = 0x4,  // JSON对象
};


#pragma pack(2)
struct Header
{
	short contenttype;  // 报文内容码
	short opcode;  // 操作码
	short statuscode;  // 状态码
	int length;  // 报文长度
};
#pragma pack()


class Message
{
private:
	short __contenttype;  // 报文内容码
	short __opcode;  // 操作码
	short __statuscode;  // 状态码
	std::string __content;  // 
	neb::CJsonObject *__json = nullptr;  //

public:
	Message(short contenttype = ContentType::NONE, short opcode = 0, short statuscode = 0, const std::string &content = "")
		: __contenttype(contenttype), __opcode(opcode), __statuscode(statuscode), __content(content)
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
		: __contenttype(msg.__contenttype), __opcode(msg.__opcode), __statuscode(msg.__statuscode), __content(msg.__content)
	{
		this->__json = new neb::CJsonObject(msg.__json);
	}

	~Message() {
		delete __json;
	}

	Message(Header &header, const std::string &content)
		: Message(header.contenttype, header.opcode, header.statuscode, content)
	{
	}

	static Message HeaderOnlyMsg(short opcode = 0, short statuscode = 0) {
		return Message(ContentType::HEADERONLY, opcode, statuscode);
	}

	static Message PlainTextMsg(short opcode = 0, short statuscode = 0, const std::string &text = "") {
		return Message(ContentType::PLAINTEXT, opcode, statuscode, text);
	}

	static Message JsonMsg(short opcode, short statuscode, neb::CJsonObject &json) {
		Message msg = Message(ContentType::JSONOBJRCT, opcode, statuscode);
		msg.__json = new neb::CJsonObject(json);
		return msg;
	}

	bool isValid() {
		return this->__contenttype != ContentType::NONE && this->__contenttype != ContentType::ERROR_;
	}

	/*获取报文内容码*/
	short contenttype() {
		return this->__contenttype;
	}

	/*获取操作码*/
	short opcode() {
		return this->__opcode;
	}

	/*获取状态码*/
	short statuscode() {
		return this->__statuscode;
	}

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

	std::string toString() const {
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
		Header header = Header{ __contenttype, __opcode, __statuscode, length };
		char buf[HEADER_LENGTH];
		memcpy_s(buf, sizeof(buf), &header, HEADER_LENGTH);
		return std::string(buf, HEADER_LENGTH) + cont;
	}

	static Message fromString(const std::string &data) {
		if (data.size() < HEADER_LENGTH)
			return Message();
		Header header;
		memcpy_s(&header, HEADER_LENGTH, data.c_str(), HEADER_LENGTH);
		return Message(header, data.substr(HEADER_LENGTH));
	}

};
