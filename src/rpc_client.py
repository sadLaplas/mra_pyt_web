import socket
import struct
import xml.etree.ElementTree as xml_tree

from .rpc_server import (
    OPERATIONS,
    receive_exactly,
    value_from_xml,
    value_to_xml,
)


class RPCClient:
    def __init__(self, host="127.0.0.1", port=5000):
        self.host = host
        self.port = port

    def call(self, operation, *arguments):
        request_body = xml_tree.tostring(
            value_to_xml(arguments, "arguments"), encoding="utf-8"
        )
        with socket.create_connection((self.host, self.port)) as connection:
            connection.sendall(
                struct.pack("<IH", len(request_body), operation) + request_body
            )
            header = receive_exactly(connection, 6)
            body_size, _ = struct.unpack("<IH", header)
            response_body = receive_exactly(connection, body_size)

        response = xml_tree.fromstring(response_body)
        if response.tag == "error":
            raise ValueError(value_from_xml(response))
        return value_from_xml(response)

    def create_user(self, record):
        return self.call(1, record)

    def delete_user(self, key):
        return self.call(2, key)

    def get_users(self):
        return self.call(3)

    def create_message(self, record):
        return self.call(4, record)

    def delete_message(self, key):
        return self.call(5, key)

    def get_messages(self):
        return self.call(6)

    def create_output(self, record):
        return self.call(7, record)

    def delete_output(self, key):
        return self.call(8, key)

    def get_outputs(self):
        return self.call(9)

    def recent_messages_with_outputs(self, now=None):
        if now is None:
            return self.call(10)
        return self.call(10, now)
