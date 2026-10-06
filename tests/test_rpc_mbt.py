import queue
import socket
import threading
import unittest
from xml.etree.ElementTree import fromstring

from hypothesis import settings, strategies as st
from hypothesis.stateful import (
    RuleBasedStateMachine,
    initialize,
    invariant,
    rule,
    run_state_machine_as_test,
)

from src import model
from src.rpc_client import RPCClient
from src.rpc_server import HEADER, make_body, receive_exactly, run_server


NOW = 1000
BOUNDARY = NOW - model.FIVE_MINUTES
KEYS = st.integers(0, 5)
TEXT = st.text(max_size=8)
TIMES = st.sampled_from((BOUNDARY - 1, BOUNDARY, BOUNDARY + 1, NOW))
USER_RECORDS = st.tuples(KEYS, TIMES, TEXT)
MESSAGE_RECORDS = st.tuples(KEYS, TIMES, TEXT, KEYS, TEXT, TIMES)
OUTPUT_RECORDS = st.tuples(KEYS, TIMES, TEXT, TEXT, TEXT, KEYS, KEYS)
WAIT_SECONDS = 5
UNKNOWN_OPERATION = 65535
BAD_REQUESTS = (
    (UNKNOWN_OPERATION, make_body("arguments", ())),
    (1, b"<bad"),
    (1, make_body("arguments", ())),
    (1, make_body("wrong", ())),
    (1, b'<arguments type="str">bad</arguments>'),
    (1, b'<arguments type="tuple"><item type="int">'
     b'bad</item></arguments>'),
    (1, b'<arguments type="unknown" />'),
    (1, b'<arguments type="str" encoding="base64">!</arguments>'),
)


def start_server():
    stop_event = threading.Event()
    ready = queue.Queue()
    thread = threading.Thread(
        target=run_server,
        kwargs={"port": 0, "stop_event": stop_event, "ready": ready},
        daemon=True,
    )
    thread.start()
    try:
        host, port = ready.get(timeout=WAIT_SECONDS)
    except queue.Empty:
        stop_event.set()
        thread.join(WAIT_SECONDS)
        raise AssertionError("Сервер не запустился") from None
    return RPCClient(host, port), (stop_event, thread)


def stop_server(control):
    stop_event, thread = control
    stop_event.set()
    thread.join(WAIT_SECONDS)
    assert not thread.is_alive(), "Сервер не остановился"


def send_test_response(server, operation):
    connection, _ = server.accept()
    with connection:
        size, _ = HEADER.unpack(receive_exactly(connection, HEADER.size))
        receive_exactly(connection, size)
        body = make_body("wrong", ())
        connection.sendall(HEADER.pack(len(body), operation) + body)


class RPCStateMachine(RuleBasedStateMachine):
    def __init__(self):
        super().__init__()
        model.USERS.clear()
        model.MESSAGES.clear()
        model.OUTPUTS.clear()
        self.users = {}
        self.messages = {}
        self.outputs = {}
        self.client, self.control = start_server()

    def teardown(self):
        stop_server(self.control)

    def compare(self, method, arguments, result, error=False):
        try:
            actual = getattr(self.client, method)(*arguments)
        except (ValueError, TypeError):
            assert error, f"Неожиданная ошибка: {method}"
        else:
            assert not error, f"Ожидалась ошибка: {method}"
            assert actual == result

    @initialize(timestamp=TIMES, text=TEXT)
    def initial_scenario(self, timestamp, text):
        self.connected_records(timestamp, text, True)
        for key in (10, 11):
            self.create_user((key, NOW, text))
            self.create_message((key, NOW, text, key, text, NOW))
            self.create_output((key, NOW, text, text, text, key, key))
        self.recent_messages_with_outputs()
        self.delete_output(11)
        self.delete_message(11)
        self.delete_user(11)
        self.delete_output(10)
        self.delete_message(10)
        self.delete_user(10)
        self.delete_output(99)
        self.delete_message(99)
        self.delete_user(99)
        self.get_users()
        self.get_messages()
        self.get_outputs()
        self.recent_messages_with_outputs()
        self.recent_messages_with_outputs_current_time()
        for case in range(len(BAD_REQUESTS)):
            self.bad_request(case)
        self.bad_response(True)
        self.bad_response(False)
        self.unsupported_value(True)

    @invariant()
    def tables_match_reference(self):
        assert self.client.get_users() == tuple(self.users.values())
        assert self.client.get_messages() == tuple(self.messages.values())
        assert self.client.get_outputs() == tuple(self.outputs.values())

    @rule(record=USER_RECORDS)
    def create_user(self, record):
        key = record[0]
        error = key in self.users
        self.compare("create_user", (record,), record, error)
        if not error:
            self.users[key] = record

    @rule(key=KEYS)
    def delete_user(self, key):
        error = key not in self.users or any(
            message[3] == key for message in self.messages.values()
        )
        self.compare("delete_user", (key,), self.users.get(key), error)
        if not error:
            del self.users[key]

    @rule()
    def get_users(self):
        self.compare("get_users", (), tuple(self.users.values()))

    @rule(record=MESSAGE_RECORDS)
    def create_message(self, record):
        key = record[0]
        error = key in self.messages or record[3] not in self.users
        self.compare("create_message", (record,), record, error)
        if not error:
            self.messages[key] = record

    @rule(key=KEYS)
    def delete_message(self, key):
        error = key not in self.messages or any(
            output[5] == key for output in self.outputs.values()
        )
        self.compare("delete_message", (key,), self.messages.get(key), error)
        if not error:
            del self.messages[key]

    @rule()
    def get_messages(self):
        self.compare("get_messages", (), tuple(self.messages.values()))

    @rule(record=OUTPUT_RECORDS)
    def create_output(self, record):
        key = record[0]
        error = key in self.outputs or record[5] not in self.messages
        self.compare("create_output", (record,), record, error)
        if not error:
            self.outputs[key] = record

    @rule(key=KEYS)
    def delete_output(self, key):
        error = key not in self.outputs
        self.compare("delete_output", (key,), self.outputs.get(key), error)
        if not error:
            del self.outputs[key]

    @rule()
    def get_outputs(self):
        self.compare("get_outputs", (), tuple(self.outputs.values()))

    @rule()
    def recent_messages_with_outputs(self):
        expected = {
            (message[2], output[2], user[2])
            for message in self.messages.values()
            for output in self.outputs.values()
            for user in self.users.values()
            if message[3] == user[0]
            if output[5] == message[0]
            if user[1] > BOUNDARY
        }
        actual = self.client.recent_messages_with_outputs(NOW)
        assert set(actual) == expected
        assert len(actual) == len(expected)

    @rule()
    def recent_messages_with_outputs_current_time(self):
        self.compare("recent_messages_with_outputs", (), ())

    @rule(kind=st.sampled_from(("user", "message", "output")))
    def invalid_record(self, kind):
        records = {
            "user": ((99, "bad", "web"), (99, NOW), 99),
            "message": (
                (99, NOW, "data", 99, "new"),
                (99, NOW, 99, 99, "new", NOW),
            ),
            "output": (
                (99, NOW, "reply", "done", "", 99),
                (99, NOW, "reply", "done", "", 99, "bad"),
            ),
        }
        for record in records[kind]:
            self.compare("create_" + kind, (record,), None, True)

    @rule(timestamp=TIMES, text=TEXT, duplicate=st.booleans())
    def connected_records(self, timestamp, text, duplicate):
        key = max((*self.users, *self.messages, *self.outputs), default=100)
        key += 1
        user = (key, timestamp, text)
        message = (key, NOW, text, key, "new", NOW)
        output = (key, NOW, text, "done", "", key, 0)
        self.create_user(user)
        self.create_message(message)
        self.create_output(output)
        self.create_user(user)
        self.create_message(message)
        self.create_output(output)
        if duplicate:
            self.create_output((key + 1,) + output[1:])
        self.recent_messages_with_outputs()
        self.delete_user(key)
        self.delete_message(key)
        if duplicate:
            self.delete_output(key + 1)
        self.delete_output(key)
        self.delete_message(key)
        self.delete_user(key)

    @rule(case=st.integers(0, len(BAD_REQUESTS) - 1))
    def bad_request(self, case):
        operation, body = BAD_REQUESTS[case]
        with socket.create_connection(
            (self.client.host, self.client.port), timeout=WAIT_SECONDS
        ) as connection:
            connection.sendall(HEADER.pack(len(body), operation) + body)
            size, actual_operation = HEADER.unpack(
                receive_exactly(connection, HEADER.size)
            )
            response = fromstring(receive_exactly(connection, size))
        assert actual_operation == operation
        assert response.tag == "error"

    @rule(wrong_code=st.booleans())
    def bad_response(self, wrong_code):
        operation = UNKNOWN_OPERATION if wrong_code else 3
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server:
            server.bind(("127.0.0.1", 0))
            server.listen()
            server.settimeout(WAIT_SECONDS)
            thread = threading.Thread(
                target=send_test_response,
                args=(server, operation),
                daemon=True,
            )
            thread.start()
            client = RPCClient(*server.getsockname())
            try:
                client.get_users()
            except ValueError:
                pass
            else:
                raise AssertionError("Клиент принял неправильный ответ")
            finally:
                thread.join(WAIT_SECONDS)
            assert not thread.is_alive()

    @rule(value=st.booleans())
    def unsupported_value(self, value):
        self.compare("create_user", ((99, NOW, value),), None, True)

    @rule(part=st.sampled_from((b"\x01\x00", HEADER.pack(8, 3))))
    def disconnect(self, part):
        with socket.create_connection(
            (self.client.host, self.client.port), timeout=WAIT_SECONDS
        ) as connection:
            connection.sendall(part)
        self.get_users()


STATE_MACHINE_SETTINGS = settings(
    max_examples=30,
    stateful_step_count=50,
    deadline=None,
    derandomize=True,
    database=None,
)


def test_state_machine():
    run_state_machine_as_test(
        RPCStateMachine, settings=STATE_MACHINE_SETTINGS
    )


def load_tests(loader, tests, pattern):
    del loader, tests, pattern
    return unittest.TestSuite((unittest.FunctionTestCase(test_state_machine),))
