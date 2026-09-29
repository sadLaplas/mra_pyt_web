from time import time

from .rpc_client import RPCClient


client = RPCClient()
timestamp = int(time())

print(client.create_user((1, timestamp, "web")))
print(client.get_users())
print(client.create_message((1, timestamp, "message", 1, "new", timestamp)))
print(client.get_messages())
print(client.create_output((1, timestamp, "response", "done", "", 1, 0)))
print(client.get_outputs())
print(client.recent_messages_with_outputs())
print(client.delete_output(1))
print(client.delete_message(1))
print(client.delete_user(1))
