# -*- coding: utf-8 -*-
from typing import Optional, Union, Any, Self
from enum import IntEnum
import json

class ContentType(IntEnum):
    NONE = 0x0  # 空报文
    ERROR_ = 0x1  # 错误报文
    HEADERONLY = 0x2  # 只含报头
    PLAINTEXT = 0x3  # 纯文本内容
    JSONOBJRCT = 0x4  # JSON对象
    BINARY = 0x5  # 二进制串


class MessageConfig:
    ENCODING = "UTF-8"


class Header:
    HEADER_LENGTH = 10

    def __init__(self, contenttype, opcode, statuscode, length):
        self.contenttype: int = contenttype  # 报文内容码
        self.opcode: int = opcode  # 操作码
        self.statuscode: int = statuscode  # 状态码
        self.length: int = length  # 报文长度
    
    def toBytes(self) -> bytes:
        """转换为二进制流"""
        header = b""
        header += self.contenttype.to_bytes(2, 'little', signed=False)  # 报文内容码
        header += self.opcode.to_bytes(2, 'little', signed=False)  # 操作码
        header += self.statuscode.to_bytes(2, 'little', signed=False)  # 状态码
        header += self.length.to_bytes(4, 'little', signed=False)  # 报文长度
        return header

    @classmethod
    def fromBytes(cls, data: bytes) -> Optional["Header"]:
        """二进制流转换为Header

        如果转换失败返回None。
        """
        if len(data) != cls.HEADER_LENGTH:
            return None
        contenttype = int.from_bytes(data[0:2], 'little', signed=False)  # 报文内容码
        opcode = int.from_bytes(data[2:4], 'little', signed=False)  # 操作码
        statuscode = int().from_bytes(data[4:6], 'little', signed=False)  # 响应码
        length = int().from_bytes(data[6:10], 'little', signed=False)  # 文本内容起始位置
        return cls(contenttype, opcode, statuscode, length)


class Message:
    def __init__(self, contenttype: ContentType = ContentType.NONE, opcode: int = 0, statuscode: int = 0, content: Union[str, bytes] = ""):
        self.__contenttype: int = contenttype  # 报文内容码
        self.__opcode: int = opcode  # 操作码
        self.__statuscode: int = statuscode  # 响应码
        self.__content: Union[str, bytes] = ""
        self.__json: dict = {}
        
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
                    raise ValueError("content does not match ContentType")
    
    @classmethod
    def HeaderContent(cls, header: Header, content: Union[str, bytes]) -> Self:
        """由Header和正文内容组成Message"""
        if header is None:
            return Message()
        msg = Message(header.contenttype, header.opcode, header.statuscode, content)
        return msg

    @classmethod
    def HeaderOnlyMsg(cls, opcode: int = 0, statuscode: int = 0) -> Self:
        """不含正文的Message"""
        msg = Message(ContentType.HEADERONLY, opcode, statuscode)
        return msg
        
    @classmethod
    def PlainTextMsg(cls, opcode: int = 0, statuscode: int = 0, text: str = "") -> Self:
        """正文为纯文本的Message"""
        msg = Message(ContentType.PLAINTEXT, opcode, statuscode)
        msg.__content = text
        return msg
        
    @classmethod
    def JsonMsg(cls, opcode: int = 0, statuscode: int = 0, dict_: dict = None, **kw) -> Self:
        """正文为json对象的Message

        Args:
            opcode (int): 操作码.
            statuscode (int): 状态码.
            dict_ (dict): 转换为json的字典.
            **kw: 自动转换为json字段.
        """
        msg = Message(ContentType.JSONOBJRCT, opcode, statuscode)
        if dict_ is not None:
            msg.__json = dict_
        for key in kw.keys():
            if kw[key] is not None:
                msg.__json[key] = kw[key]
        return msg

    @classmethod
    def BinaryMsg(cls, opcode: int = 0, statuscode: int = 0, content: bytes = b"") -> Self:
        """正文为二进制(自定义解析方式)的Message"""
        msg = Message(ContentType.BINARY, opcode, statuscode)
        msg.__content = content
        return msg

    def isValid(self) -> bool:
        """是否为非空/非错误包"""
        return self.__contenttype != ContentType.NONE and self.__contenttype != ContentType.ERROR_

    def get(self, key: str) -> Any:
        """当正文为JSONOBJRCT类型时获取json值

        Args:
            key (str): json键名

        Returns:
            Any: json值
        """
        ret = self.__json.get(key)
        return ret

    def content(self) -> Union[str, bytes]:
        """直接获取正文"""
        return self.__content

    def contenttype(self) -> int:
        """获取内容码"""
        return self.__contenttype
        
    def opcode(self) -> int:
        """获取操作码"""
        return self.__opcode

    def statuscode(self) -> int:
        """获取状态码"""
        return self.__statuscode
        
    def toBytes(self) -> bytes:
        """转换为二进制流

        Raises:
            ValueError: 当正文内容与类型不匹配时抛出。
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
                raise ValueError("content does not match ContentType")
        length = len(content)  # 数据包长度(不包含报头)
        header = Header(self.__contenttype, self.__opcode, self.__statuscode, length)
        return header.toBytes() + content

    @classmethod
    def fromBytes(cls, data: bytes) -> Self:
        if len(data) < Header.HEADER_LENGTH:
            return Message()
        header = Header.fromBytes(data[0:Header.HEADER_LENGTH])
        if header == None:
            return Message()
        if header.contenttype == ContentType.BINARY:
            msg = Message.HeaderContent(header, data[Header.HEADER_LENGTH:])
        else:
            msg = Message.HeaderContent(header, data[Header.HEADER_LENGTH:].decode(MessageConfig.ENCODING))
        return msg

    def __str__(self):
        return (f"pro:{self.__contenttype}  op:{self.__opcode}  sta:{self.__statuscode}\n"
                f"content:\n{self.__content}")
    
    def __repr__(self):
        return str(self)
