using System.Net.Sockets;

namespace hsocket;


public class HTcpReqResClient : HTcpClient
{
    public HTcpReqResClient() : base() { }

    public override bool SendMsg(Message msg)
    {
        try
        {
            tcpSocket.SendMsg(msg);
            return true;
        }
        catch (ObjectDisposedException) { }
        catch (SocketException)
        {
            OnDisconnected();
            Close();
        }
        return false;
    }

    protected override bool GetFTTransferPort()
    {
        try
        {
            Message msg = tcpSocket.RecvMsg();
            if (msg.Opcode == (ushort)BuiltInOpCode.FT_TRANSFER_PORT)
            {
                ftServerPort = msg.GetInt("port") ?? 0;
                return true;
            }
        }
        catch (ObjectDisposedException) { }
        catch (SocketException) { }
        catch (MessageError) { }
        catch (InvalidOperationException) { }
        return false;
    }

    /// <summary>
    /// 发送一个请求报文，接收一个响应报文
    /// </summary>
    /// <param name="msg">发送的报文</param>
    /// <returns>接收到的响应报文，失败时返回null</returns>
    public Message? Request(Message msg)
    {
        if (SendMsg(msg))
        {
            try
            {
                Message response = tcpSocket.RecvMsg();
                return response;
            }
            catch (ObjectDisposedException) { return null; }
            catch (SocketException) { }
            catch (MessageError) { }  // 收到空包文时断开
            OnDisconnected();
            Close();
        }
        return null;
    }
}
