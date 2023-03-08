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
        }
        catch (SocketException)
        {
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
        try
        {
            Message msg = tcpSocket.RecvMsg();
            if (msg.Opcode == (ushort)BuiltInOpCode.FT_TRANSFER_PORT)
            {
                ftServerPort = msg.GetInt("port") ?? 0;
                return true;
            }
            else
                return false;
        }
        catch (SocketException)
        {
            return false;
        }
        catch (MessageError)
        {
            return false;
        }
    }

    public Message? Request(Message msg)
    {
        if (SendMsg(msg))
        {
            try
            {
                Message response = tcpSocket.RecvMsg();
                return response;
            }
            catch (SocketException) { }
            catch (MessageError) { }  // 收到空包文时断开
            OnDisconnected();
            Close();
            return null;
        }
        return null;
    }
}
