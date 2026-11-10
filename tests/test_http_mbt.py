"""Сгенерированные сценарии HTTP API с файловым хранилищем."""

from http.client import HTTPConnection
from http import HTTPStatus
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from threading import Thread
import unittest
from urllib.error import HTTPError

from hypothesis import settings, strategies as st
from hypothesis.stateful import RuleBasedStateMachine, invariant, rule
from hypothesis.stateful import run_state_machine_as_test

from src.http_client import HTTPClient
from src.http_server import create_server


FUTURE_TIMESTAMP = 4102444800


class HTTPMachine(RuleBasedStateMachine):
    def __init__(self):
        super().__init__()
        self.directory = TemporaryDirectory()
        self.server = create_server(
            ("127.0.0.1", 0), Path(self.directory.name) / "store",
            test_mode=True,
        )
        self.thread = Thread(
            target=self.server.serve_forever,
            kwargs={"poll_interval": 0.01}, daemon=True,
        )
        self.thread.start()
        port = self.server.server_address[1]
        self.client = HTTPClient("http://127.0.0.1:" + str(port))
        self.users = {}
        self.messages = {}

    def teardown(self):
        self.client.close()
        self.server.shutdown()
        self.thread.join()
        self.server.server_close()
        self.server.task_pool.shutdown()
        self.directory.cleanup()

    def compare_call(self, function, argument, expected, invalid):
        try:
            actual = function(argument)
        except HTTPError as error:
            assert invalid
            assert error.code == HTTPStatus.BAD_REQUEST
            error.close()
        else:
            assert not invalid
            assert actual == expected

    @rule(
        key=st.integers(0, 3),
        timestamp=st.sampled_from((0, FUTURE_TIMESTAMP)),
    )
    def make_user(self, key, timestamp):
        row = [key, timestamp, "web"]
        invalid = key in self.users
        self.compare_call(self.client.make_user, row, row, invalid)
        if not invalid:
            self.users[key] = row

    @rule(key=st.integers(0, 3))
    def pop_user(self, key):
        invalid = key not in self.users or any(
            row[3] == key for row in self.messages.values()
        )
        self.compare_call(
            self.client.pop_user, key, self.users.get(key), invalid
        )
        if not invalid:
            del self.users[key]

    @rule(key=st.integers(0, 3), user=st.integers(0, 3))
    def make_message(self, key, user):
        row = [key, 1000, json.dumps({"code": "1234567"}), user, "new", 0]
        invalid = key in self.messages or user not in self.users
        try:
            actual = self.client.make_message(row)
        except HTTPError as error:
            assert invalid and error.code == HTTPStatus.BAD_REQUEST
            error.close()
        else:
            assert not invalid
            assert actual[:4] == row[:4]
            assert actual[4] == "queued"
            assert isinstance(actual[5], int)
            self.messages[key] = actual

    @rule(key=st.integers(0, 3))
    def pop_message(self, key):
        invalid = key not in self.messages
        self.compare_call(
            self.client.pop_message, key, self.messages.get(key), invalid
        )
        if not invalid:
            del self.messages[key]
        assert self.client.all_output(key) == []

    @rule(user=st.integers(0, 3), message=st.integers(0, 3))
    def search(self, user, message):
        expected = [row for row in self.messages.values() if row[3] == user]
        assert sorted(self.client.all_message(user)) == sorted(expected)
        outputs = self.client.all_output(message)
        assert len(outputs) == int(message in self.messages)
        if outputs:
            assert outputs[0][2:] == ["test", "done", "", message, 0]
        assert self.client.all_user({"key": user}) == (
            [self.users[user]] if user in self.users else []
        )

    @rule(content=st.booleans(), language=st.booleans())
    def required_headers(self, content, language):
        headers = {}
        if content:
            headers["Content-Type"] = "application/json"
        if language:
            headers["Accept-Language"] = "en"
        connection = HTTPConnection(*self.server.server_address)
        connection.request(
            "POST", "/private/api/report/all", body="{}", headers=headers
        )
        response = connection.getresponse()
        assert response.status == (
            HTTPStatus.UNSUPPORTED_MEDIA_TYPE if not content else (
                HTTPStatus.NOT_ACCEPTABLE if not language else HTTPStatus.OK
            )
        )
        response.read()
        connection.close()

    @rule(case=st.sampled_from((
        ("POST", "/unknown", "{}", 404),
        ("POST", "/private/api/unknown/all", "{}", 404),
        ("POST", "/private/api/user/unknown", "{}", 404),
        ("POST", "/private/api/user/all", "[]", 400),
        ("POST", "/private/api/user/all", '{"unknown": 1}', 400),
        ("POST", "/private/api/user/make", "{}", 400),
        ("POST", "/private/api/user/make", "[]", 400),
        ("POST", "/private/api/message/make", "[]", 400),
        ("POST", "/private/api/report/all", "bad", 400),
        ("DELETE", "/private/api/user/pop/bad", "{}", 400),
        ("GET", "/private/api/user/all", "{}", 404),
    )))
    def invalid_requests(self, case):
        method, route, body, status = case
        connection = HTTPConnection(*self.server.server_address)
        connection.request(method, route, body=body, headers={
            "Content-Type": "application/json", "Accept-Language": "en",
        })
        response = connection.getresponse()
        assert response.status == status
        response.read()
        connection.close()

    @invariant()
    def tables_and_report_match(self):
        assert sorted(self.client.all_user()) == sorted(self.users.values())
        expected = {
            (row[2], "test", "web") for row in self.messages.values()
            if self.users[row[3]][1] == FUTURE_TIMESTAMP
        }
        actual = self.client.all_report()
        assert {tuple(row) for row in actual} == expected
        assert len(actual) == len(expected)


def test_file():
    run_state_machine_as_test(
        HTTPMachine, settings=settings(
            max_examples=20, stateful_step_count=35, deadline=None,
            derandomize=True, database=None,
        ),
    )


def load_tests(loader, tests, pattern):
    return unittest.TestSuite((unittest.FunctionTestCase(test_file),))
