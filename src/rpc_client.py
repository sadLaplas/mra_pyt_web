"""Клиент с десятью методами, соответствующими функциям модели."""

import socket
import xml.etree.ElementTree as xml_tree

from .rpc_server import (
    CONNECTION_TIMEOUT,
    HEADER,
    HOST,
    PORT,
    make_body,
    receive_exactly,
    value_from_xml,
)


class RPCClient:
    """Отправлять по одному вызову на TCP-соединение."""

    def __init__(self, host=HOST, port=PORT):
        self.host = host
        self.port = port

    def call(self, operation, *arguments):
        body = make_body("arguments", arguments)
        with socket.create_connection(
            (self.host, self.port), timeout=CONNECTION_TIMEOUT
        ) as connection:
            connection.sendall(HEADER.pack(len(body), operation) + body)
            size, response_operation = HEADER.unpack(
                receive_exactly(connection, HEADER.size)
            )
            response = xml_tree.fromstring(receive_exactly(connection, size))
        if response_operation != operation:
            raise ValueError("Неверный код операции в ответе")
        if response.tag == "error":
            raise ValueError(value_from_xml(response))
        if response.tag != "result":
            raise ValueError("Ожидается элемент result")
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
