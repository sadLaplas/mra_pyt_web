import socket
import struct
import xml.etree.ElementTree as ET

import model


OPERATIONS = {
    1: "create_user",
    2: "delete_user",
    3: "get_users",
    4: "create_message",
    5: "delete_message",
    6: "get_messages",
    7: "create_output",
    8: "delete_output",
    9: "get_outputs",
    10: "recent_messages_with_outputs",
}


def receive_exactly(connection, size):
    data = b""
    while len(data) < size:
        part = connection.recv(size - len(data))
        if not part:
            raise ConnectionError("Соединение закрыто")
        data += part
    return data


def value_to_xml(value, tag):
    element = ET.Element(tag)
    if isinstance(value, tuple):
        element.set("type", "tuple")
        for item in value:
            element.append(value_to_xml(item, "item"))
    elif isinstance(value, int):
        element.set("type", "int")
        element.text = str(value)
    else:
        element.set("type", "str")
        element.text = value
    return element


def value_from_xml(element):
    value_type = element.get("type")
    if value_type == "tuple":
        return tuple(value_from_xml(item) for item in element)
    if value_type == "int":
        return int(element.text)
    return element.text or ""


def make_body(tag, value):
    return ET.tostring(value_to_xml(value, tag), encoding="utf-8")


class RPCServer:
    def __init__(self, host="127.0.0.1", port=5000):
        self.host = host
        self.port = port

    def serve_forever(self):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server:
            server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            server.bind((self.host, self.port))
            server.listen()
            print(f"RPC-сервер запущен: {self.host}:{self.port}")
            while True:
                connection, _ = server.accept()
                with connection:
                    self.handle_connection(connection)

    def handle_connection(self, connection):
        header = receive_exactly(connection, 6)
        body_size, operation = struct.unpack("<IH", header)
        body = receive_exactly(connection, body_size)
        arguments = value_from_xml(ET.fromstring(body))
        print(f"RPC request: {OPERATIONS[operation]}{arguments}")

        try:
            result = getattr(model, OPERATIONS[operation])(*arguments)
            response_body = make_body("result", result)
        except ValueError as error:
            response_body = make_body("error", str(error))

        connection.sendall(struct.pack("<IH", len(response_body), operation) + response_body)
        print(f"RPC response: {response_body.decode('utf-8')}")


if __name__ == "__main__":
    RPCServer().serve_forever()
