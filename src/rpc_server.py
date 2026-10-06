"""TCP RPC варианта 6: XML, заголовок <IH, журнал в stdout."""

import socket
import struct
import xml.etree.ElementTree as xml_tree
from base64 import b64decode, b64encode
from binascii import Error as Base64Error

from .model import FUNCTIONS


HOST = "127.0.0.1"
PORT = 5000
HEADER = struct.Struct("<IH")
POLL_INTERVAL = 0.1
CONNECTION_TIMEOUT = 5
FIRST_OPERATION = 1
LAST_OPERATION = len(FUNCTIONS)
OPERATIONS = dict(enumerate(FUNCTIONS, start=FIRST_OPERATION))


def receive_exactly(connection, size):
    """Прочитать ровно size байтов даже при фрагментации TCP."""
    data = b""
    while len(data) < size:
        part = connection.recv(size - len(data))
        if not part:
            raise ConnectionError("Соединение закрыто")
        data += part
    return data


def value_to_xml(value, tag):
    """Кодировать кортеж, int или str с явным указанием типа."""
    element = xml_tree.Element(tag)
    if isinstance(value, tuple):
        element.set("type", "tuple")
        for item in value:
            element.append(value_to_xml(item, "item"))
    elif type(value) is int:
        element.set("type", "int")
        element.text = str(value)
    elif type(value) is str:
        element.set("type", "str")
        element.set("encoding", "base64")
        element.text = b64encode(value.encode("utf-8")).decode("ascii")
    else:
        raise TypeError("XML поддерживает tuple, int и str")
    return element


def value_from_xml(element):
    """Восстановить кортежи и скалярные значения из XML."""
    value_type = element.get("type")
    if value_type == "tuple":
        return tuple(value_from_xml(item) for item in element)
    if value_type == "int":
        return int(element.text or "")
    if value_type == "str":
        if element.get("encoding") == "base64":
            return b64decode(element.text or "", validate=True).decode("utf-8")
        return element.text or ""
    raise ValueError("Неизвестный тип XML")


def make_body(tag, value):
    """Создать XML-тело в байтах UTF-8."""
    return xml_tree.tostring(value_to_xml(value, tag), encoding="utf-8")


def execute_request(operation, body):
    """Выполнить одну из десяти функций или вернуть XML-ошибку."""
    try:
        function = OPERATIONS.get(operation)
        if function is None:
            raise ValueError("Неизвестный код операции")
        root = xml_tree.fromstring(body)
        if root.tag != "arguments":
            raise ValueError("Ожидается элемент arguments")
        arguments = value_from_xml(root)
        if not isinstance(arguments, tuple):
            raise ValueError("Ожидается кортеж аргументов")
        return make_body("result", function(*arguments))
    except (ValueError, TypeError, Base64Error, xml_tree.ParseError) as error:
        return make_body("error", str(error))


def handle_connection(connection):
    """Прочитать запрос, вывести запрос и ответ, отправить ответ."""
    header = receive_exactly(connection, HEADER.size)
    body_size, operation = HEADER.unpack(header)
    body = receive_exactly(connection, body_size)
    print(f"RPC request: op={operation}, body={body!r}", flush=True)
    response = execute_request(operation, body)
    print(f"RPC response: {response.decode('utf-8')}", flush=True)
    connection.sendall(HEADER.pack(len(response), operation) + response)


def serve_connections(server, stop_event=None):
    """Обрабатывать подключения до сигнала остановки."""
    while stop_event is None or not stop_event.is_set():
        try:
            connection, _ = server.accept()
        except socket.timeout:
            continue
        with connection:
            connection.settimeout(CONNECTION_TIMEOUT)
            try:
                handle_connection(connection)
            except OSError as error:
                print(f"RPC transport error: {error}", flush=True)


def run_server(host=HOST, port=PORT, stop_event=None, ready=None):
    """Запустить сервер; ready при наличии получает (host, port)."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server:
        server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server.bind((host, port))
        server.listen()
        server.settimeout(POLL_INTERVAL)
        address = server.getsockname()
        print(f"RPC server: {address}", flush=True)
        if ready is not None:
            ready.put(address)
        serve_connections(server, stop_event)


if __name__ == "__main__":
    run_server()
