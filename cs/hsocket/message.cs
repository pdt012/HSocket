using System.Text;
using System.Text.Json.Nodes;

namespace hsocket
{
    /// <summary>
    /// Base class of message error.
    /// </summary>
    class MessageError : ApplicationException { };

    /// <summary>
    /// Received an empty message.
    /// </summary>
    class EmptyMessageError : ApplicationException { };

    /// <summary>
    /// Error in loading a message header.
    /// </summary>
    class MessageHeaderError : ApplicationException { };

    public enum ContentType : ushort
    {
        HEADERONLY = 0x1,  // 只含报头
        PLAINTEXT = 0x2,  // 纯文本内容
        JSONOBJRCT = 0x3,  // JSON对象
        BINARY = 0x4,  // 二进制串
    }

    public class Header
    {
        public const int HEADER_LENGTH = 8;

        public ContentType contenttype;  // 报文内容码
        public ushort opcode;  // 操作码
        public int length;  // 报文长度

        public Header(ContentType contenttype, ushort opcode, int length)
        {
            this.contenttype = contenttype;
            this.opcode = opcode;
            this.length = length;
        }

        public byte[] ToBytes()
        {
            byte[] header = new byte[HEADER_LENGTH];
            BitConverter.GetBytes((ushort)this.contenttype).CopyTo(header, 0);
            BitConverter.GetBytes(this.opcode).CopyTo(header, 2);
            BitConverter.GetBytes(this.length).CopyTo(header, 4);
            return header;
        }

        /// <summary>
        /// 二进制流转换为Header
        /// </summary>
        /// <exception cref="EmptyMessageError">收到空报文时抛出</exception>
        /// <exception cref="MessageHeaderError">报头解析异常时抛出</exception>
        public static Header FromBytes(byte[] data)
        {
            if (data.Length == 0)
                throw new EmptyMessageError();
            if (data.Length != HEADER_LENGTH)
                throw new MessageHeaderError();
            ushort contenttype = BitConverter.ToUInt16(data.AsSpan(0, 2));
            ushort opcode = BitConverter.ToUInt16(data.AsSpan(2, 4));
            int length = BitConverter.ToInt32(data.AsSpan(4, 4));
            return new Header((ContentType)contenttype, opcode, length);
        }
    }

    public class Message
    {
        private ContentType contenttype;  // 报文内容码
        private ushort opcode;  // 操作码
        // 以下字段同时只有一个生效（根据contenttype）
        private string? text;
        private JsonObject? json;
        private byte[]? binary;

        public Message(ContentType contenttype, ushort opcode)
        {
            this.contenttype = contenttype;
            this.opcode = opcode;
        }

        /// <summary>
        /// 由Header和二进制内容组成Message
        /// </summary>
        public Message(Header header, byte[] content)
            : this(header.contenttype, header.opcode)
        {
            switch (contenttype)
            {
                case ContentType.HEADERONLY:
                    break;
                case ContentType.PLAINTEXT:
                    this.text = Encoding.UTF8.GetString(content);
                    break;
                case ContentType.JSONOBJRCT:
                    JsonNode? node = JsonNode.Parse(this.binary);
                    this.json = node?.AsObject();
                    break;
                case ContentType.BINARY:
                    this.binary = content;
                    break;
            }
        }

        /// <summary>
        /// 不含正文的Message
        /// </summary>
        public static Message HeaderOnlyMsg(ushort opcode)
        {
            return new Message(ContentType.HEADERONLY, opcode);
        }

        /// <summary>
        /// 正文为纯文本的Message
        /// </summary>
        public static Message PlainTextMsg(ushort opcode, string text)
        {
            return new Message(ContentType.PLAINTEXT, opcode)
            {
                text = text
            };
        }

        /// <summary>
        /// 正文为json对象的Message
        /// </summary>
        public static Message JsonMsg(ushort opcode, JsonObject json)
        {
            // return new Message(ContentType.HEADERONLY, opcode);
            return new(ContentType.JSONOBJRCT, opcode)
            {
                json = json
            };
        }

        /// <summary>
        /// 正文为二进制(自定义解析方式)的Message
        /// </summary>
        public static Message BinaryMsg(ushort opcode, byte[] binary)
        {
            return new Message(ContentType.BINARY, opcode)
            {
                binary = binary
            };
        }

        public ContentType Contenttype { get { return this.contenttype; } }

        public ushort Opcode { get { return this.opcode; } }

        public string? Text { get { return this.text; } }

        public JsonObject? Json { get { return this.json; } }

        public byte[]? Binary { get { return this.binary; } }

        public int? GetInt(string key)
        {
            JsonNode? node = this.json?[key];
            return node?.GetValue<int>();
        }

        public float? GetFloat(string key)
        {
            JsonNode? node = this.json?[key];
            return node?.GetValue<float>();
        }

        public bool? GetBool(string key)
        {
            JsonNode? node = this.json?[key];
            return node?.GetValue<bool>();
        }

        public string? GetStr(string key)
        {
            JsonNode? node = this.json?[key];
            return node?.GetValue<string>();
        }

        public byte[] ToBytes()
        {
            byte[] cont = Array.Empty<byte>();
            switch (this.contenttype)
            {
                case ContentType.HEADERONLY:
                    break;
                case ContentType.PLAINTEXT:
                    cont = Encoding.UTF8.GetBytes(this.text ?? "");
                    break;
                case ContentType.JSONOBJRCT:
                    string jsonStr = this.json != null ? this.json.ToJsonString() : "";
                    cont = Encoding.UTF8.GetBytes(jsonStr);
                    break;
                case ContentType.BINARY:
                    cont = this.binary ?? Array.Empty<byte>();
                    break;
            }
            Header header = new(contenttype, opcode, cont.Length);
            byte[] headerData = header.ToBytes();
            byte[] data = new byte[headerData.Length + cont.Length];
            headerData.CopyTo(data, 0);
            cont.CopyTo(data, headerData.Length);
            return data;
        }

        public static Message FromBytes(byte[] data)
        {
            Header header = Header.FromBytes(data[0..Header.HEADER_LENGTH]);
            return new Message(header, data[Header.HEADER_LENGTH..]);
        }

        public override string ToString()
        {
            return string.Format("<Message>({0}) opcode:{1}\n",
                    Enum.GetName(this.contenttype), this.opcode)
                + string.Format("content:\n{0}", this.binary);
        }
    }
}
