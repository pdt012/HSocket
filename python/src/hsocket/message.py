# -*- coding: utf-8 -*-
from typing import Optional, Union, Any, Self
from enum import IntEnum
import json


class MessageError(Exception):
    """Base class of message error."""
    ...


class EmptyMessageError(MessageError):
    """Received an empty message."""
    ...


class MessageHeaderError(MessageError):
    """error in loading a message header."""
    ...


class MessageTypeError(MessageError):
    """Content of message does not match contenttype."""
    ...


class ContentType(IntEnum):
    HEADERONLY = 0x1  # 只含报头
    PLAINTEXT = 0x2  # 纯文本内容
    JSONOBJRCT = 0x3  # JSON对象
    BINARY = 0x4  # 二进制串


class MessageConfig:
    ENCODING = "UTF-8"


class Header:
    HEADER_LENGTH = 8

    def __init__(self, contenttype, opcode, length):
        self.contenttype: ContentType = contenttype  # 报文内容码
        self.opcode: int = opcode  # 操作码
        self.length: int = length  # 报文长度

    def toBytes(self) -> bytes:
        """转换为二进制流"""
        header = b""
        header += self.contenttype.to_bytes(2, 'little', signed=False)  # 报文内容码
        header += self.opcode.to_bytes(2, 'little', signed=False)  # 操作码
        header += self.length.to_bytes(4, 'little', signed=False)  # 报文长度
        return header

    @classmethod
    def fromBytes(cls, data: bytes) -> Self:
        """二进制流转换为Header

        Raises:
            EmptyMessageError: 收到空报文时抛出
            MessageHeaderError: 报头解析异常时抛出
        """
        if not data:
            raise EmptyMessageError()
        if len(data) != cls.HEADER_LENGTH:
            raise MessageHeaderError()
        contenttype = int.from_bytes(data[0:2], 'little', signed=False)  # 报文内容码
        opcode = int.from_bytes(data[2:4], 'little', signed=False)  # 操作码
        length = int().from_bytes(data[4:8], 'little', signed=False)  # 报文长度
        return cls(contenttype, opcode, length)


class Message:
    def __init__(self, contenttype: ContentType, opcode: int = 0, content: Union[str, bytes] = ""):
        """Message

        Raises:
            MessageTypeError: 当正文内容与类型不匹配时抛出
        """
        self.__contenttype: ContentType = contenttype  # 报文内容码
        self.__opcode: int = opcode  # 操作码
        self.__content: Union[str, bytes] = ""
        self.__json: Optional[dict] = None

        if content:
            match self.__contenttype:
                case ContentType.HEADERONLY:
                    pass
                case ContentType.PLAINTEXT if isinstance(content, str):
                    self.__content = content
                case ContentType.JSONOBJRCT if isinstance(content, str):
                    self.__content = content
                    self.__json = json.loads(content)
                case ContentType.BINARY if isinstance(content, bytes):
                    self.__content = content
                case _:
                    raise MessageTypeError("content does not match ContentType")

    @classmethod
    def HeaderContent(cls, header: Header, content: Union[str, bytes]) -> Self:
        """由Header和正文内容组成Message"""
        return Message(header.contenttype, header.opcode, content)

    @classmethod
    def HeaderOnlyMsg(cls, opcode: int = 0) -> Self:
        """不含正文的Message"""
        return Message(ContentType.HEADERONLY, opcode)

    @classmethod
    def PlainTextMsg(cls, opcode: int = 0, text: str = "") -> Self:
        """正文为纯文本的Message"""
        msg = Message(ContentType.PLAINTEXT, opcode)
        msg.__content = text
        return msg

    @classmethod
    def JsonMsg(cls, opcode: int = 0, dict_: dict = None, **kw) -> Self:
        """正文为json对象的Message

        Args:
            opcode (int): 操作码.
            dict_ (dict): 转换为json的字典.
            **kw: 自动转换为json字段.
        """
        msg = Message(ContentType.JSONOBJRCT, opcode)
        if dict_ is not None:
            msg.__json = dict_
        else:
            msg.__json = {}
        for key in kw.keys():
            if kw[key] is not None:
                msg.__json[key] = kw[key]
        return msg

    @classmethod
    def BinaryMsg(cls, opcode: int = 0, content: bytes = b"") -> Self:
        """正文为二进制(自定义解析方式)的Message"""
        msg = Message(ContentType.BINARY, opcode)
        msg.__content = content
        return msg

    def get(self, key: str) -> Any:
        """当正文为JSONOBJRCT类型时获取json值

        Args:
            key (str): json键名

        Raises:
            MessageTypeError: 正文内容不为json时抛出

        Returns:
            Any: json值
        """
        if self.__contenttype == ContentType.JSONOBJRCT:
            ret = self.__json.get(key)
            return ret
        else:
            raise MessageTypeError("need a JSONOBJRCT message")

    def content(self) -> Union[str, bytes]:
        """直接获取正文"""
        return self.__content

    def contenttype(self) -> ContentType:
        """获取内容码"""
        return self.__contenttype

    def opcode(self) -> int:
        """获取操作码"""
        return self.__opcode

    def toBytes(self) -> bytes:
        """转换为二进制流

        Raises:
            MessageTypeError: 当正文内容与类型不匹配时抛出
        """
        match self.__contenttype:
            case ContentType.HEADERONLY:
                content = b""
            case ContentType.PLAINTEXT if isinstance(self.__content, str):
                content = self.__content.encode(MessageConfig.ENCODING)
            case ContentType.JSONOBJRCT if isinstance(self.__content, str):
                content = json.dumps(self.__json).encode(MessageConfig.ENCODING)
            case ContentType.BINARY if isinstance(self.__content, bytes):
                content = self.__content
            case _:
                raise MessageTypeError("content does not match ContentType")
        length = len(content)  # 数据包长度(不包含报头)
        header = Header(self.__contenttype, self.__opcode, length)
        return header.toBytes() + content

    @classmethod
    def fromBytes(cls, data: bytes) -> Self:
        """二进制流转换为Message

        Args:
            data (bytes): _description_

        Raises:
            EmptyMessageError: 收到空报文时抛出
            MessageHeaderError: 报头解析异常时抛出
            UnicodeDecodeError: 报文内容编码异常时抛出

        Returns:
            Self: _description_
        """
        header = Header.fromBytes(data[0:Header.HEADER_LENGTH])
        if header.contenttype == ContentType.BINARY:
            msg = Message.HeaderContent(header, data[Header.HEADER_LENGTH:])
        else:
            msg = Message.HeaderContent(header, data[Header.HEADER_LENGTH:].decode(MessageConfig.ENCODING))
        return msg

    def __str__(self):
        return (f"<Message>({ContentType(self.__contenttype).name}) opcode:{self.__opcode}\n"
                f"content:\n{self.__content}")

    def __repr__(self):
        return str(self)
