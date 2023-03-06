using hsocket;
using System.Text.Json.Nodes;

Message msg = Message.PlainTextMsg(2, "helloworld");
Console.WriteLine(msg);


JsonObject obj = new JsonObject();
obj.Add("aaa", 12345);
obj.Add("bbb", "bbbvalue");
Console.WriteLine(obj.ToJsonString());

msg = Message.JsonMsg(2, obj);
Console.WriteLine(msg);