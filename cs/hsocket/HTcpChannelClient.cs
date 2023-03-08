using System.Net;
using System.Net.Sockets;

namespace hsocket;


public class HTcpChannelClient : HTcpClient
{
    public delegate bool OnMessageReceivedCallback(Message mag);

    public event OnMessageReceivedCallback? OnMessageReceivedEvent;
    private readonly Dictionary<ushort, OnMessageReceivedCallback> OnMsgRecvByOpCodeCallbackDict = new();

    private readonly Thread thMessage;
    private readonly Mutex mtxFTPort = new();

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

    public void SetOnMsgRecvByOpCodeCallback(ushort opcode, OnMessageReceivedCallback callback)
    {
        if (OnMsgRecvByOpCodeCallbackDict.TryGetValue(opcode, out _))
            OnMsgRecvByOpCodeCallbackDict[opcode] = callback;
        else
            OnMsgRecvByOpCodeCallbackDict.Add(opcode, callback);
    }

    public void PopOnMsgRecvByOpCodeCallback(ushort opcode)
    {
        OnMsgRecvByOpCodeCallbackDict.Remove(opcode);
    }

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
