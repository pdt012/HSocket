using System.Net;
using System.Net.Sockets;
using System.Text.Json.Nodes;

namespace hsocket;


enum BuiltInOpCode : ushort
{
    FT_TRANSFER_PORT = 60020,  // 文件传输端口{ "port": port }
    FT_SEND_FILES_HEADER = 62000
}


public abstract class HTcpClient
{
    public delegate void OnConnectedCallback();
    public delegate void OnDisconnectedCallback();

    public event OnConnectedCallback? OnConnectedEvent;
    public event OnDisconnectedCallback? OnDisconnectedEvent;

    protected HTcpSocket tcpSocket = new();
    protected IPAddress? ftServerIp = null;
    protected int ftServerPort = 0;

    public HTcpClient()
    {
        tcpSocket.Blocking = true;
    }

    public HTcpSocket Socket()
    {
        return tcpSocket;
    }

    public virtual void Connect(IPEndPoint addr)
    {
        tcpSocket.Connect(addr);
        ftServerIp = addr.Address;
        OnConnected();
    }

    public virtual void Close()
    {
        tcpSocket.Close();
    }

    public virtual bool IsClosed()
    {
        return !tcpSocket.IsValid();
    }

    public abstract bool SendMsg(Message msg);

    protected abstract bool GetFTTransferPort();

    public void SendFile(string path, string filename)
    {
        if (ftServerIp == null)
            throw new NullReferenceException("ftServerIp is null");
        if (!GetFTTransferPort())
            return;
        // send
        using HTcpSocket ftSocket = new();
        try
        {
            ftSocket.Connect(new IPEndPoint(ftServerIp, ftServerPort));
            using FileStream fin = File.OpenRead(path);
            ftSocket.SendFile(fin, filename);
        }
        catch (SocketException)
        {
            return;
        }
        catch (FileNotFoundException e)
        {
            Console.WriteLine(e.Message);
            return;
        }
    }

    public string RecvFile()
    {
        if (ftServerIp == null)
            throw new NullReferenceException("'ftServerIp' is null.");
        if (!GetFTTransferPort())
            return "";
        // recv
        using HTcpSocket ftSocket = new();
        try
        {
            ftSocket.Connect(new IPEndPoint(ftServerIp, ftServerPort));
            string downloadPath = ftSocket.RecvFile();
            return downloadPath;
        }
        catch (SocketException)
        {
            return "";
        }
    }

    public int SendFiles(List<string> paths, List<string> filenames)
    {
        if (ftServerIp == null)
            throw new NullReferenceException("'ftServerIp' is null.");
        if (paths.Count != filenames.Count)
            throw new ArgumentException("Length of 'paths' & 'filenames' is not matched.");
        if (!GetFTTransferPort())
            return 0;
        // send files header
        int countSent = 0;
        using HTcpSocket ftSocket = new();
        try
        {
            ftSocket.Connect(new IPEndPoint(ftServerIp, ftServerPort));
            JsonObject json = new()
            {
                { "file_count", paths.Count }
            };
            Message filesHeaderMsg = Message.JsonMsg((ushort)BuiltInOpCode.FT_SEND_FILES_HEADER, json);
            ftSocket.SendMsg(filesHeaderMsg);
        }
        catch (SocketException)
        {
            return countSent;
        }
        // send files
        for (int i = 0; i < paths.Count; i++)
        {
            string path = paths[i];
            string filename = filenames[i];
            try
            {
                using FileStream fin = File.OpenRead(path);
                ftSocket.SendFile(fin, filename);
                countSent++;
            }
            catch (FileNotFoundException e)
            {
                Console.WriteLine(e.Message);
                continue;
            }
            catch (SocketException)
            {
                break;
            }
        }
        return countSent;
    }

    public List<string> RecvFiles()
    {
        if (ftServerIp == null)
            throw new NullReferenceException("'ftServerIp' is null.");
        if (!GetFTTransferPort())
            return new List<string>();
        // recv
        List<string> downloadPathList = new();
        using HTcpSocket ftSocket = new();
        try
        {
            ftSocket.Connect(new IPEndPoint(ftServerIp, ftServerPort));
            Message filesHeaderMsg = ftSocket.RecvMsg();
            int fileCount = filesHeaderMsg.GetInt("file_count") ?? 0;
            // recv files
            for (int i = 0; i < fileCount; i++)
            {
                try
                {
                    string downloadPath = ftSocket.RecvFile();
                    if (downloadPath.Length > 0)
                        downloadPathList.Add(downloadPath);
                }
                catch (SocketException)
                {
                    break;
                }
            }
        }
        catch (SocketException) { }
        catch (MessageError) { }
        return downloadPathList;
    }

    protected void OnConnected()
    {
        OnConnectedEvent?.Invoke();
    }
    protected void OnDisconnected()
    {
        OnDisconnectedEvent?.Invoke();
    }
}

