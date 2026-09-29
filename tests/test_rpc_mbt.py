import socket
import struct
import threading
import unittest
import xml.etree.ElementTree as xml_tree

from hypothesis import settings, strategies as st
from hypothesis.stateful import (
    RuleBasedStateMachine,
    initialize,
    invariant,
    run_state_machine_as_test,
    rule,
)

from src import model
from src.rpc_client import RPCClient
from src.rpc_server import RPCServer, receive_exactly


NOW = 1000
server = None
server_thread = None
stop_event = threading.Event()


def start_server():
    global server, server_thread
    stop_event.clear()
    ready_event = threading.Event()
    server = RPCServer(port=0, stop_event=stop_event, ready_event=ready_event)
    server_thread = threading.Thread(target=server.serve_forever, daemon=True)
    server_thread.start()
    assert ready_event.wait(5), "RPC-сервер не запустился"


def stop_server():
    stop_event.set()
    server_thread.join(5)
    assert not server_thread.is_alive(), (
        "RPC-сервер не остановился"
    )


class RPCStateMachine(RuleBasedStateMachine):
    def __init__(self):
        super().__init__()
        self.client = RPCClient(port=server.port)

    @initialize()
    def reset(self):
        model.USERS.clear()
        model.MESSAGES.clear()
        model.OUTPUTS.clear()
        self.users = {}
        self.messages = {}
        self.outputs = {}

    def compare(self, method, arguments, result, error):
        try:
            actual = getattr(self.client, method)(*arguments)
        except ValueError:
            assert error
        else:
            assert not error
            assert actual == result

    @invariant()
    def tables_match_reference(self):
        assert self.client.get_users() == tuple(self.users.values())
        assert self.client.get_messages() == tuple(self.messages.values())
        assert self.client.get_outputs() == tuple(self.outputs.values())

    @rule(
        key=st.integers(0, 5),
        timestamp=st.sampled_from((699, 700, 701, NOW)),
        platform=st.text(alphabet="abc", max_size=5),
    )
    def create_user(self, key, timestamp, platform):
        record = (key, timestamp, platform)
        error = key in self.users
        self.compare("create_user", (record,), record, error)
        if not error:
            self.users[key] = record

    @rule(key=st.integers(0, 5))
    def delete_user(self, key):
        error = key not in self.users or any(
            message[3] == key for message in self.messages.values()
        )
        result = self.users.get(key)
        self.compare("delete_user", (key,), result, error)
        if not error:
            del self.users[key]

    @rule()
    def get_users(self):
        self.compare("get_users", (), tuple(self.users.values()), False)

    @rule(
        key=st.integers(0, 5),
        timestamp=st.integers(700, NOW),
        data=st.text(alphabet="abc", max_size=5),
        user=st.integers(0, 5),
        stage=st.text(alphabet="abc", max_size=5),
        enqueued=st.integers(700, NOW),
    )
    def create_message(self, key, timestamp, data, user, stage, enqueued):
        record = (key, timestamp, data, user, stage, enqueued)
        error = key in self.messages or user not in self.users
        self.compare("create_message", (record,), record, error)
        if not error:
            self.messages[key] = record

    @rule(key=st.integers(0, 5))
    def delete_message(self, key):
        error = key not in self.messages or any(
            output[5] == key for output in self.outputs.values()
        )
        result = self.messages.get(key)
        self.compare("delete_message", (key,), result, error)
        if not error:
            del self.messages[key]

    @rule()
    def get_messages(self):
        self.compare("get_messages", (), tuple(self.messages.values()), False)

    @rule(
        record=st.tuples(
            st.integers(0, 5),
            st.integers(700, NOW),
            st.text(alphabet="abc", max_size=5),
            st.text(alphabet="abc", max_size=5),
            st.text(alphabet="abc", max_size=5),
            st.integers(0, 5),
            st.integers(0, 1),
        )
    )
    def create_output(self, record):
        key = record[0]
        message = record[5]
        error = key in self.outputs or message not in self.messages
        self.compare("create_output", (record,), record, error)
        if not error:
            self.outputs[key] = record

    @rule(key=st.integers(0, 5))
    def delete_output(self, key):
        error = key not in self.outputs
        result = self.outputs.get(key)
        self.compare("delete_output", (key,), result, error)
        if not error:
            del self.outputs[key]

    @rule()
    def get_outputs(self):
        self.compare("get_outputs", (), tuple(self.outputs.values()), False)

    @rule()
    def recent_messages_with_outputs(self):
        expected = set()
        for user in self.users.values():
            if user[1] <= NOW - 300:
                continue
            for message in self.messages.values():
                if message[3] != user[0]:
                    continue
                for output in self.outputs.values():
                    if output[5] == message[0]:
                        expected.add((message[2], output[2], user[2]))
        actual = self.client.recent_messages_with_outputs(NOW)
        assert set(actual) == expected
        assert len(actual) == len(expected)

    @rule()
    def recent_messages_with_outputs_current_time(self):
        self.compare("recent_messages_with_outputs", (), (), False)

    @rule(kind=st.sampled_from(("user", "message", "output")))
    def invalid_record(self, kind):
        records = {
            "user": ((99, "bad", "web"), (99, 1000), (True, 1000, "web")),
            "message": (
                (99, 1000, "data", 0, "new"),
                (99, 1000, "data", 0, "new", False),
            ),
            "output": (
                (99, 1000, "response", "done", "", 0),
                (99, 1000, "response", "done", "", 0, False),
            ),
        }
        for record in records[kind]:
            self.compare("create_" + kind, (record,), None, True)

    @rule(timestamp=st.sampled_from((699, 700, 701)), duplicate=st.booleans())
    def connected_records(self, timestamp, duplicate):
        user_key = max(self.users, default=100) + 1
        message_key = max(self.messages, default=100) + 1
        output_key = max(self.outputs, default=100) + 1
        user = (user_key, timestamp, "web")
        message = (message_key, NOW, "data", user_key, "new", NOW)
        output = (output_key, NOW, "response", "done", "", message_key, 0)

        self.compare("create_user", (user,), user, False)
        self.users[user_key] = user
        self.compare("create_message", (message,), message, False)
        self.messages[message_key] = message
        self.compare("create_output", (output,), output, False)
        self.outputs[output_key] = output

        if duplicate:
            second = (
                output_key + 1, NOW, "response", "done", "", message_key, 0
            )
            self.compare("create_output", (second,), second, False)
            self.outputs[second[0]] = second

        self.recent_messages_with_outputs()
        self.compare("delete_user", (user_key,), None, True)
        self.compare("delete_message", (message_key,), None, True)

        output_keys = (
            (output_key, output_key + 1)
            if duplicate
            else (output_key,)
        )
        for key in output_keys:
            self.compare("delete_output", (key,), self.outputs[key], False)
            del self.outputs[key]
        self.compare("delete_message", (message_key,), message, False)
        del self.messages[message_key]
        self.compare("delete_user", (user_key,), user, False)
        del self.users[user_key]


STATE_MACHINE_SETTINGS = settings(
    max_examples=30,
    stateful_step_count=50,
    deadline=None,
    derandomize=True,
    database=None,
)


def test_state_machine():
    start_server()
    try:
        run_state_machine_as_test(
            RPCStateMachine,
            settings=STATE_MACHINE_SETTINGS,
        )
    finally:
        stop_server()


def test_bad_requests_and_disconnect():
    start_server()
    try:
        empty = b'<arguments type="tuple" />'
        cases = (
            (999, empty),
            (1, b"<bad"),
            (1, empty),
            (1, b'<wrong type="tuple" />'),
            (1, b'<arguments type="str">bad</arguments>'),
            (
                1,
                b'<arguments type="tuple">'
                b'<item type="int">bad</item></arguments>',
            ),
        )
        for operation, body in cases:
            with socket.create_connection(
                (server.host, server.port)
            ) as connection:
                header = struct.pack("<IH", len(body), operation)
                connection.sendall(header + body)
                size, response_operation = struct.unpack(
                    "<IH", receive_exactly(connection, 6)
                )
                response = xml_tree.fromstring(
                    receive_exactly(connection, size)
                )
            assert response_operation == operation
            assert response.tag == "error"

        with socket.create_connection(
            (server.host, server.port)
        ) as connection:
            connection.sendall(b"\x01\x00")
        assert RPCClient(port=server.port).get_users() == ()
    finally:
        stop_server()


def load_tests(loader, tests, pattern):
    del loader, tests, pattern
    return unittest.TestSuite(
        (
            unittest.FunctionTestCase(test_state_machine),
            unittest.FunctionTestCase(test_bad_requests_and_disconnect),
        )
    )
