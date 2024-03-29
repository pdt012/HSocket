﻿using System.Net;
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

    /// <summary>
    /// 向服务端发送报文
    /// </summary>
    /// <param name="msg">发送的报文</param>
    /// <returns>是否成功</returns>
    public abstract bool SendMsg(Message msg);

    /// <summary>
    /// 获取服务端的文件传输端口
    /// </summary>
    /// <returns>是否成功获取</returns>
    protected abstract bool GetFTTransferPort();

    /// <summary>
    /// 发送一个文件
    /// </summary>
    /// <param name="path">文件路径</param>
    /// <param name="filename">文件名</param>
    /// <exception cref="NullReferenceException"></exception>
    public void SendFile(string path, string filename)
    {
        if (ftServerIp == null)
            throw new NullReferenceException("ftServerIp is null");
        if (!GetFTTransferPort())
            return;
        // send
        using HTcpSocket ftSocket = new();
        FileStream? fin = null;
        try
        {
            ftSocket.Connect(new IPEndPoint(ftServerIp, ftServerPort));
            try
            {
                fin = File.OpenRead(path);
            }
            catch (Exception e)
            {
                Console.WriteLine(e.Message);
                return;
            }
            ftSocket.SendFile(fin, filename);
        }
        catch
        {
            return;
        }
        finally
        {
            fin?.Close();
        }
    }

    /// <summary>
    /// 接收一个文件
    /// </summary>
    /// <returns>下载的文件路径，失败时返回空字符串</returns>
    /// <exception cref="NullReferenceException"></exception>
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
        catch
        {
            return "";
        }
    }

    /// <summary>
    /// 发送多个文件
    /// </summary>
    /// <param name="paths">文件路径列表</param>
    /// <param name="filenames">文件名列表</param>
    /// <returns>成功发送的文件数</returns>
    /// <exception cref="NullReferenceException"></exception>
    /// <exception cref="ArgumentException"></exception>
    public List<string> SendFiles(List<string> paths, List<string> filenames)
    {
        if (ftServerIp == null)
            throw new NullReferenceException("'ftServerIp' is null.");
        if (!GetFTTransferPort())
            return new();
        // send
        List<string> succeedPathList = new();
        using HTcpSocket ftSocket = new();
        try
        {
            ftSocket.Connect(new IPEndPoint(ftServerIp, ftServerPort));
            ftSocket.SendFiles(paths, filenames, ref succeedPathList);
        }
        catch (ArgumentException) { throw; }
        catch { }
        return succeedPathList;
    }

    /// <summary>
    /// 接收多个文件
    /// </summary>
    /// <returns>下载的文件路径列表</returns>
    /// <exception cref="NullReferenceException"></exception>
    public List<string> RecvFiles()
    {
        if (ftServerIp == null)
            throw new NullReferenceException("'ftServerIp' is null.");
        if (!GetFTTransferPort())
            return new List<string>();
        // recv
        List<string> downloadPathList = new();
        try
        {
            using HTcpSocket ftSocket = new();
            ftSocket.Connect(new IPEndPoint(ftServerIp, ftServerPort));
            ftSocket.RecvFiles(ref downloadPathList);
        }
        catch { }
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

