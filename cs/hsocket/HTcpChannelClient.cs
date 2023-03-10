using System.Net;
using System.Net.Sockets;

namespace hsocket;


public class HTcpChannelClient : HTcpClient
{
    /// <summary>
    /// 收到报文时的回调
    /// </summary>
    /// <param name="mag">收到的报文</param>
    /// <returns>是否消化该事件(不在向下传递)</returns>
    public delegate bool OnMessageReceivedCallback(Message mag);

    public event OnMessageReceivedCallback? OnMessageReceivedEvent;
    private readonly Dictionary<ushort, OnMessageReceivedCallback> OnMsgRecvByOpCodeCallbackDict = new();

    private readonly Thread thMessage;
    private readonly Mutex mtxFTPort = new();

    /// <summary>
    /// 文件传输的超时时长
    /// </summary>
    public int FtTimeout { get; set; }

    public HTcpChannelClient() : base()
    {
        thMessage = new Thread(new ThreadStart(MessageHandle));
    }

    public override void Connect(IPEndPoint addr)
    {
        base.Connect(addr);
        thMessage.Start();
    }

    public override bool SendMsg(Message msg)
    {
        try
        {
            tcpSocket.SendMsg(msg);
        }
        catch (ObjectDisposedException)
        {
            return false;
        }
        catch (SocketException)
        {
            thMessage?.Join();  // make sure that 'onDisconnected' only runs once
            if (!IsClosed())
            {
                OnDisconnected();
                Close();
            }
            return false;
        }
        return true;
    }

    protected override bool GetFTTransferPort()
    {
        return mtxFTPort.WaitOne(FtTimeout);
    }

    private void MessageHandle()
    {
        while (!IsClosed())
        {
            try
            {
                Message msg = tcpSocket.RecvMsg();
                if (msg.Opcode == (ushort)BuiltInOpCode.FT_TRANSFER_PORT)
                {
                    ftServerPort = msg.GetInt("port") ?? 0;
                    mtxFTPort.ReleaseMutex();
                    continue;
                }
                OnMessageReceived(msg);
            }
            catch (SocketException e)
            {
                if (e.SocketErrorCode == SocketError.TimedOut)
                    continue;
                OnDisconnected();
                Close();
                break;
            }
            catch (MessageError)
            {
                OnDisconnected();
                Close();
                break;
            }
        }
    }

    /// <summary>
    /// 设置收到指定操作码报文时的回调
    /// </summary>
    /// <param name="opcode">操作码</param>
    /// <param name="callback">回调方法</param>
    public void SetOnMsgRecvByOpCodeCallback(ushort opcode, OnMessageReceivedCallback callback)
    {
        if (OnMsgRecvByOpCodeCallbackDict.TryGetValue(opcode, out _))
            OnMsgRecvByOpCodeCallbackDict[opcode] = callback;
        else
            OnMsgRecvByOpCodeCallbackDict.Add(opcode, callback);
    }

    /// <summary>
    /// 取消收到指定操作码报文时的回调
    /// </summary>
    /// <param name="opcode">操作码</param>
    public void PopOnMsgRecvByOpCodeCallback(ushort opcode)
    {
        OnMsgRecvByOpCodeCallbackDict.Remove(opcode);
    }

    /// <summary>
    /// 设置收到报文时的回调(调用晚于<see cref="SetOnMsgRecvByOpCodeCallback"/>设置的回调)
    /// </summary>
    /// <param name="callback">回调方法</param>
    public void SetOnMessageReceivedCallback(OnMessageReceivedCallback callback)
    {
        OnMessageReceivedEvent = callback;
    }

    protected bool OnMessageReceived(Message msg)
    {
        // callback by opcode
        OnMsgRecvByOpCodeCallbackDict.TryGetValue(msg.Opcode, out OnMessageReceivedCallback? callback);
        if (callback != null)
        {
            bool finished = callback(msg);
            if (finished)
                return true;
        }
        // default callback
        return OnMessageReceivedEvent?.Invoke(msg) ?? false;
    }
}
