"""Hypothesis проверяет subprocess, PNG и границы формулы (6)."""

from base64 import b64decode
from contextlib import contextmanager
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from threading import Thread
from time import monotonic, sleep, time
import unittest

from hypothesis import given, settings, strategies as st

from src.ean8 import generate_png
from src.http_client import HTTPClient
from src.http_server import create_server
from src.http_store import report


EXPECTED_OUTPUT_COUNT = 1
TASK_TIMEOUT = 10
POLL_INTERVAL = 0.01


@contextmanager
def running_server(path):
    server = create_server(("127.0.0.1", 0), path)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    port = server.server_address[1]
    client = HTTPClient("http://127.0.0.1:" + str(port))
    try:
        yield server, client
    finally:
        client.close()
        server.shutdown()
        thread.join()
        server.task_pool.shutdown()
        server.server_close()


def wait_for_output(client):
    deadline = monotonic() + TASK_TIMEOUT
    outputs = client.all_output(1)
    while not outputs and monotonic() < deadline:
        sleep(POLL_INTERVAL)
        outputs = client.all_output(1)
    assert len(outputs) == EXPECTED_OUTPUT_COUNT
    return outputs[0]


def verify_output(output, code, valid):
    if valid:
        assert output[3] == "done"
        assert b64decode(output[2]) == generate_png(code)
    else:
        assert output[3] == "failed"
        assert output[4]


def verify_persistence(path, expected):
    reopened = create_server(("127.0.0.1", 0), path, test_mode=True)
    try:
        actual = reopened.read_data()
        assert json.dumps(actual) == json.dumps(expected)
    finally:
        reopened.task_pool.shutdown()
        reopened.server_close()


@settings(max_examples=6, deadline=None)
@given(valid=st.booleans())
def check_async_task(valid):
    with TemporaryDirectory() as directory:
        path = Path(directory) / "store"
        with running_server(path) as (server, client):
            client.make_user((1, int(time()), "web"))
            code = "9638507" if valid else "bad"
            data = json.dumps({"code": code})
            client.make_message((1, 0, data, 1, "new", 0))
            verify_output(wait_for_output(client), code, valid)
            persisted = server.read_data()
        verify_persistence(path, persisted)


@given(delta=st.sampled_from((-1, 0, 1)), duplicate=st.booleans())
def check_formula(delta, duplicate):
    output = (1, 1000, "png", "done", "", 1, 0)
    data = {
        "user": [(1, 700 + delta, "web")],
        "message": [(1, 1000, "code", 1, "done", 1000),
                    (2, 1000, "orphan", 99, "done", 1000)],
        "output": [output, (3, 1000, "orphan", "done", "", 2, 0)],
    }
    if duplicate:
        data["output"].append((2, *output[1:]))
    assert report(data, now=1000) == (
        (("code", "png", "web"),) if delta > 0 else ()
    )


def load_tests(loader, tests, pattern):
    return unittest.TestSuite((
        unittest.FunctionTestCase(check_async_task),
        unittest.FunctionTestCase(check_formula),
    ))
