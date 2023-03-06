using System.Net;
using System.Net.Sockets;
using System.Text;

namespace hsocket;


static class SocketConfig
{
    public static int recvBufferSize = 1024;
    public static int fileBufferSize = 2048;
    public static string downloadPath = "download/";
}


public class HSocket : Socket
{
    protected HSocket(AddressFamily addressFamily, SocketType socketType, ProtocolType protocolType)
        : base(addressFamily, socketType, protocolType)
    { }
    protected HSocket(SafeSocketHandle safeSocketHandle)
        : base(safeSocketHandle)
    { }

    public bool IsValid()
    {
        return !SafeHandle.IsInvalid;
    }
}

public class HTcpSocket : HSocket

{
    public HTcpSocket()
        : base(AddressFamily.InterNetwork, SocketType.Stream, ProtocolType.Tcp)
    { }

    protected HTcpSocket(SafeSocketHandle safeSocketHandle)
        : base(safeSocketHandle)
    { }

    public new HTcpSocket Accept()
    {
        Socket sock = base.Accept();
        return new HTcpSocket(sock.SafeHandle);
    }

    public void SendMsg(Message msg)
    {
        Send(msg.ToBytes());
    }

    public Message RecvMsg()
    {
        byte[] headerBuffer = new byte[Header.HEADER_LENGTH];
        Receive(headerBuffer);
        Header header = Header.FromBytes(headerBuffer);
        int size = header.Length;
        List<byte> data = new();
        while (data.Count < size)
        {
            int tryRecvSize = Math.Min(size - data.Count, SocketConfig.recvBufferSize);
            byte[] recvBuffer = new byte[tryRecvSize];
            int receivedSize = Receive(recvBuffer);
            data.AddRange(recvBuffer[0..receivedSize]);
        }
        return new Message(header, data.ToArray());
    }

    public void SendFile(FileStream file, string filename)
    {
        // get file size
        long filesize = file.Length;
        // file header
        Send(Encoding.UTF8.GetBytes(filename));  // filename
        Send(new byte[1] { 0 });  // name end
        Send(BitConverter.GetBytes(filesize));  // filesize
        // file content
        while (true)
        {
            byte[] fileBuffer = new byte[SocketConfig.fileBufferSize];
            int readSize = file.Read(fileBuffer, 0, fileBuffer.Length);
            if (readSize == 0)
                break;
            Send(fileBuffer, 0, readSize, SocketFlags.None);
        }
    }

    public string RecvFile()
    {
        // filename
        List<byte> filenameBuffer = new();
        while (true)
        {
            byte[] byteBuffer = new byte[1];
            int recvSize = Receive(byteBuffer);
            if (recvSize == 0)
                return "";
            else if (byteBuffer[0] != 0)
                filenameBuffer.Add(byteBuffer[0]);
            else
                break;
        }
        string filename = Encoding.UTF8.GetString(filenameBuffer.ToArray());
        // filesize
        byte[] filesizeBuffer = new byte[4];
        Receive(filesizeBuffer);
        int filesize = BitConverter.ToInt32(filesizeBuffer);
        // file content
        if (filename.Length > 0 && filesize > 0)
        {
            if (!Directory.Exists(SocketConfig.downloadPath))
                Directory.CreateDirectory(SocketConfig.downloadPath);
            string downPath = Path.Join(SocketConfig.downloadPath, filename);
            int totalReceivedSize = 0;
            using (FileStream file = new(downPath, FileMode.OpenOrCreate, FileAccess.Write))
            {
                while (totalReceivedSize < filesize)
                {
                    int tryRecvSize = Math.Min(filesize - totalReceivedSize, SocketConfig.recvBufferSize);
                    byte[] recvBuffer = new byte[tryRecvSize];
                    int receivedSize = Receive(recvBuffer);
                    file.Write(recvBuffer, 0, receivedSize);
                    totalReceivedSize += receivedSize;
                }
            }
            return downPath;
        }
        else
            return "";
    }
}


public class HUdpSocket : HSocket
{
    private static readonly byte[] recvBuffer = new byte[65535];
    public HUdpSocket()
        : base(AddressFamily.InterNetwork, SocketType.Stream, ProtocolType.Tcp)
    { }

    public bool SendMsg(Message msg, EndPoint addr)
    {
        byte[] data = msg.ToBytes();
        return SendTo(data, addr) == data.Length;
    }

    public void RecvMsg(ref IPEndPoint senderAddr)
    {
        try
        {
            EndPoint senderEndPoint = senderAddr;
            int receivedSize = ReceiveFrom(recvBuffer, SocketFlags.None, ref senderEndPoint);
        }
        catch (SocketException e)
        {
            if (e.ErrorCode == 10054)  // received an ICMP unreachable
                throw new EmptyMessageError();
        }
    }
}
