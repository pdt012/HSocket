using System.Linq;
using System.Net;
using System.Net.Sockets;
using System.Text;

namespace hsocket;


static class SocketConfig
{
    public static int recvBufferSize = 1024;
    public static int fileBufferSize = 2048;
    public static string downloadDirectory = "download/";
}


public class HSocket : Socket
{
    protected HSocket(AddressFamily addressFamily, SocketType socketType, ProtocolType protocolType)
        : base(addressFamily, socketType, protocolType)
    { }
    protected HSocket(SafeSocketHandle safeSocketHandle)
        : base(safeSocketHandle)
    { }

    /// <summary>
    /// 是否为有效的套接字
    /// </summary>
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

    /// <summary>
    /// 发送一个数据包
    /// </summary>
    /// <param name="msg">发送的报文</param>
    /// <exception cref="ObjectDisposedException"></exception>
    /// <exception cref="SocketException"></exception>
    public void SendMsg(Message msg)
    {
        Send(msg.ToBytes());
    }

    /// <summary>
    /// 尝试接收一个数据包
    /// </summary>
    /// <returns>收到的报文</returns>
    /// <exception cref="ObjectDisposedException"></exception>
    /// <exception cref="SocketException"></exception>
    /// <exception cref="EmptyMessageError"></exception>
    /// <exception cref="MessageHeaderError"></exception>
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

    /// <summary>
    /// 发送一个文件
    /// </summary>
    /// <param name="file">可读的文件对象</param>
    /// <param name="filename">文件名</param>
    /// <exception cref="EncoderFallbackException"></exception>
    /// <exception cref="ObjectDisposedException"></exception>
    /// <exception cref="SocketException"></exception>
    /// <exception cref="IOException"></exception>
    public void SendFile(FileStream file, string filename)
    {
        // get file size
        int filesize = (int)file.Length;
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

    /// <summary>
    /// 尝试接收一个文件
    /// </summary>
    /// <returns>成功接收的文件路径，若接收失败则返回空字符串</returns>
    /// <exception cref="EncoderFallbackException"></exception>
    /// <exception cref="ObjectDisposedException"></exception>
    /// <exception cref="SocketException"></exception>
    /// <exception cref="IOException"></exception>
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
            if (!Directory.Exists(SocketConfig.downloadDirectory))
                Directory.CreateDirectory(SocketConfig.downloadDirectory);
            string downloadPath = Path.Join(SocketConfig.downloadDirectory, filename);
            int totalReceivedSize = 0;
            using (FileStream file = new(downloadPath, FileMode.OpenOrCreate, FileAccess.Write))
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
            return downloadPath;
        }
        else
            return "";
    }

    /// <summary>
    /// 发送多个文件
    /// </summary>
    /// <param name="pathList">文件路径列表</param>
    /// <param name="filenameList">文件名列表</param>
    /// <param name="succeedPathList">返回成功发送的文件路径列表</param>
    /// <exception cref="ArgumentException">文件路径与文件名列表长度不同时抛出</exception>
    /// <exception cref="EncoderFallbackException"></exception>
    /// <exception cref="ObjectDisposedException"></exception>
    /// <exception cref="SocketException"></exception>
    /// <exception cref="IOException"></exception>
    public void SendFiles(List<string> pathList, List<string> filenameList, ref List<string> succeedPathList)
    {
        succeedPathList.Clear();
        if (pathList.Count != filenameList.Count)
            throw new ArgumentException("Length of 'pathList' & 'filenameList' is not matched.");
        // files header
        Send(BitConverter.GetBytes(pathList.Count));  // file count
        // send files
        for (int i = 0; i < pathList.Count; i++)
        {
            string path = pathList[i];
            string filename = filenameList[i];
            FileStream? fin;
            try
            {
                fin = File.OpenRead(path);
            }
            catch (Exception e)
            {
                Console.WriteLine(e.Message);
                continue;
            }
            try
            {
                SendFile(fin, filename);
                succeedPathList.Add(path);
            }
            finally
            {
                fin?.Close();
            }
        }
    }

    /// <summary>
    /// 接收多个文件
    /// </summary>
    /// <param name="downloadPathListOut">返回下载的文件路径列表</param>
    /// <exception cref="EncoderFallbackException"></exception>
    /// <exception cref="ObjectDisposedException"></exception>
    /// <exception cref="SocketException"></exception>
    /// <exception cref="IOException"></exception>
    public void RecvFiles(ref List<string> downloadPathListOut)
    {
        downloadPathListOut.Clear();
        // files header
        byte[] fileCountBuffer = new byte[4];
        Receive(fileCountBuffer);
        int fileCount = BitConverter.ToInt32(fileCountBuffer);
        // recv files
        for (int i = 0; i < fileCount; i++)
        {
            string path = RecvFile();
            if (path.Length > 0)
                downloadPathListOut.Add(path);
        }
    }
}


public class HUdpSocket : HSocket
{
    private static readonly byte[] recvBuffer = new byte[65535];
    public HUdpSocket()
        : base(AddressFamily.InterNetwork, SocketType.Stream, ProtocolType.Tcp)
    { }

    /// <summary>
    /// 发送一个数据包
    /// </summary>
    /// <param name="msg">发送的报文</param>
    /// <param name="addr">目标地址</param>
    /// <returns>数据是否全部发送</returns>
    /// <exception cref="ObjectDisposedException"></exception>
    /// <exception cref="SocketException"></exception>
    public bool SendMsg(Message msg, EndPoint addr)
    {
        byte[] data = msg.ToBytes();
        return SendTo(data, addr) == data.Length;
    }

    /// <summary>
    /// 尝试接收一个数据包
    /// </summary>
    /// <param name="senderAddr"></param>
    /// <exception cref="EmptyMessageError"></exception>
    /// <exception cref="MessageHeaderError"></exception>
    /// <exception cref="ObjectDisposedException"></exception>
    /// <exception cref="SocketException"></exception>
    public Message RecvMsg(ref IPEndPoint senderAddr)
    {
        try
        {
            EndPoint senderEndPoint = senderAddr;
            int receivedSize = ReceiveFrom(recvBuffer, SocketFlags.None, ref senderEndPoint);
            return Message.FromBytes(recvBuffer[0..receivedSize]);
        }
        catch (SocketException e)
        {
            if (e.SocketErrorCode == SocketError.ConnectionReset)  // received an ICMP unreachable
                throw new EmptyMessageError();
            else throw;
        }
    }
}
