using hsocket;
using System.Text.Json.Nodes;
using System.Net;


static void onDisconnected()
{
    Console.WriteLine("onDisconnected");
}

try
{
    HTcpReqResClient client = new();
    client.Connect(new IPEndPoint(IPAddress.Parse("127.0.0.1"), 40000));
    client.Socket().Blocking = true;
    client.Socket().ReceiveTimeout = 5000;
    client.Socket().SendTimeout = 5000;
    client.OnDisconnectedEvent += onDisconnected;

    Console.WriteLine("start");
    while (true)
    {
        Console.Write(">>>");
        int code;
        string? line = Console.ReadLine();
        try
        {
            code = int.Parse(line ?? "");
        }
        catch (FormatException)
        {
            continue;
        }
        switch (code)
        {
            case 100:
                client.SendMsg(Message.HeaderOnlyMsg(100));
                client.SendFile("testfile/test1.txt", "test1_by_cs_client.txt");
                Console.WriteLine("send file");
                break;
            case 101:
                {
                    client.SendMsg(Message.HeaderOnlyMsg(101));
                    string path = client.RecvFile();
                    Console.WriteLine($"recv file '{path}'");
                    break;
                }
            case 110:
                {
                    client.SendMsg(Message.HeaderOnlyMsg(110));
                    List<string> pathlist = new() { "testfile/test1.txt", "testfile/test2.txt" };
                    List<string> namelist = new() { "test1_by_cs_client.txt", "test2_by_cs_client.txt" };
                    int count = client.SendFiles(pathlist, namelist);
                    Console.WriteLine($"send files ({count})");
                    break;
                }
            case 111:
                {
                    client.SendMsg(Message.HeaderOnlyMsg(111));
                    List<string> paths = client.RecvFiles();
                    Console.Write("recv files [");
                    foreach (string path in paths)
                    {
                        Console.Write($"'{path}', ");
                    }
                    Console.WriteLine("]");
                    break;
                }
            default:
                {
                    JsonObject json = new();
                    string text = $"test message<{code}> send by cs client";
                    json.Add("text", text);
                    Message msg = Message.JsonMsg((ushort)code, json);
                    Message? replyMsg = client.Request(msg);
                    if (replyMsg != null)
                    {
                        Console.WriteLine(replyMsg);
                    }
                    break;
                }
        }
    }
}
catch (Exception e)
{
    Console.WriteLine(e.ToString());
}