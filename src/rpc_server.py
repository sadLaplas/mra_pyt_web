import socket
import struct
import xml.etree.ElementTree as xml_tree

from . import model


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
    element = xml_tree.Element(tag)
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
    return xml_tree.tostring(value_to_xml(value, tag), encoding="utf-8")


def execute_request(operation, body):
    try:
        name = OPERATIONS.get(operation)
        if name is None:
            raise ValueError("Неизвестный код операции")
        root = xml_tree.fromstring(body)
        if root.tag != "arguments":
            raise ValueError("Ожидается элемент arguments")
        arguments = value_from_xml(root)
        if not isinstance(arguments, tuple):
            raise ValueError(
                "Аргументы должны быть кортежем"
            )
        return make_body("result", getattr(model, name)(*arguments))
    except (ValueError, TypeError, xml_tree.ParseError) as error:
        return make_body("error", str(error))


class RPCServer:
    def __init__(
        self, host="127.0.0.1", port=5000, stop_event=None, ready_event=None
    ):
        self.host = host
        self.port = port
        self.stop_event = stop_event
        self.ready_event = ready_event

    def serve_forever(self):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server:
            server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            server.bind((self.host, self.port))
            self.port = server.getsockname()[1]
            server.listen()
            if self.stop_event is not None:
                server.settimeout(0.1)
            if self.ready_event is not None:
                self.ready_event.set()
            print(f"RPC-сервер запущен: {self.host}:{self.port}")
            while self.stop_event is None or not self.stop_event.is_set():
                try:
                    connection, _ = server.accept()
                except socket.timeout:
                    continue
                with connection:
                    try:
                        self.handle_connection(connection)
                    except OSError as error:
                        print(f"RPC transport error: {error}")

    def handle_connection(self, connection):
        header = receive_exactly(connection, 6)
        body_size, operation = struct.unpack("<IH", header)
        body = receive_exactly(connection, body_size)
        print(f"RPC request: op={operation}, body={body!r}")
        response_body = execute_request(operation, body)

        response_header = struct.pack("<IH", len(response_body), operation)
        connection.sendall(response_header + response_body)
        print(f"RPC response: {response_body.decode('utf-8')}")


if __name__ == "__main__":
    RPCServer().serve_forever()
