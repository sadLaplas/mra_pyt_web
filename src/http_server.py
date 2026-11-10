from argparse import ArgumentParser
from concurrent.futures import ThreadPoolExecutor
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import re
import subprocess
import sys
from threading import RLock
from time import time
from urllib.parse import urlsplit

from . import http_store
from .task_runner import run_task


MAX_REQUEST_SIZE = 1024 * 1024
BODY_METHODS = ("POST", "PUT", "PATCH")
HTTP_METHODS = (*BODY_METHODS, "DELETE", "GET")
ROUTE_PATTERN = re.compile(
    r"/private/api/(user|message|output|report)/(make|pop|all)(?:/([^/]+))?"
)


def complete_task(server, message):
    try:
        response = run_task(server.command, message[2])
        stage, error = "done", ""
    except (OSError, ValueError, subprocess.SubprocessError) as failure:
        response, stage, error = "", "failed", str(failure)
    with server.data_lock:
        if server.generations.get(message[0]) is not message:
            return
        data = server.read_data()
        if not any(row[0] == message[0] for row in data["message"]):
            return
        key = max((row[0] for row in data["output"]), default=0) + 1
        data["output"].append(
            (key, int(time()), response, stage, error, message[0], 0)
        )
        data["message"] = [
            (*row[:4], stage, row[5]) if row[0] == message[0] else row
            for row in data["message"]
        ]
        server.write_data(data)


def search_records(server, data, table, body, key):
    if not isinstance(body, dict):
        raise ValueError("Search body must be an object")
    filters = dict(body)
    if key is not None:
        field = {"message": "user", "output": "message"}[table]
        filters[field] = int(key)
    return http_store.find_records(data, table, filters)


def search_report(server, data, table, body, key):
    return http_store.report(data)


def make_record(server, data, table, body, key):
    if not isinstance(body, list):
        raise ValueError("Record must be an array")
    record = tuple(body)
    if table == "message":
        http_store.validate_record(record, http_store.MESSAGE_TYPES)
        record = (*record[:4], "queued", int(time()))
    result = http_store.make_record(data, table, record)
    if table == "message" and server.test_mode:
        data["output"].append(
            (result[0], int(time()), "test", "done", "", result[0], 0)
        )
    server.write_data(data)
    if table == "message" and not server.test_mode:
        server.generations[result[0]] = result
        server.task_pool.submit(complete_task, server, result)
    return result


def pop_record(server, data, table, body, key):
    result = http_store.pop_record(data, table, int(key))
    if table == "message":
        server.generations.pop(result[0], None)
    server.write_data(data)
    return result


ROUTES = {
    ("POST", "user", "make", False): make_record,
    ("POST", "message", "make", False): make_record,
    ("DELETE", "user", "pop", True): pop_record,
    ("DELETE", "message", "pop", True): pop_record,
    ("POST", "user", "all", False): search_records,
    ("POST", "message", "all", True): search_records,
    ("POST", "output", "all", True): search_records,
    ("POST", "report", "all", False): search_report,
}


def dispatch(server, method, route, body):
    match = ROUTE_PATTERN.fullmatch(route)
    if match is None:
        raise LookupError("Unknown route")
    table, action, key = match.groups()
    handler = ROUTES.get((method, table, action, key is not None))
    if handler is None:
        raise LookupError("Unknown route")
    return handler(server, server.read_data(), table, body, key)


def validate_headers(method, headers):
    if method in BODY_METHODS and (
        headers.get("Content-Type") != "application/json"
    ):
        return HTTPStatus.UNSUPPORTED_MEDIA_TYPE, "Content-Type required"
    if headers.get("Accept-Language") != "en":
        return HTTPStatus.NOT_ACCEPTABLE, "Accept-Language required"
    return HTTPStatus.OK, ""


class RequestHandler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"
    disable_nagle_algorithm = True

    def read_body(self):
        size = int(self.headers.get("Content-Length", "0"))
        if size < 0 or size > MAX_REQUEST_SIZE:
            raise ValueError("Invalid request size")
        return json.loads(self.rfile.read(size)) if size else {}

    def execute_request(self):
        status, error = validate_headers(self.command, self.headers)
        if error:
            return status, {"error": error}
        body = self.read_body()
        with self.server.data_lock:
            result = dispatch(
                self.server, self.command, urlsplit(self.path).path, body
            )
        return HTTPStatus.OK, result

    def handle_request(self):
        try:
            status, result = self.execute_request()
        except LookupError as error:
            status, result = HTTPStatus.NOT_FOUND, {"error": str(error)}
        except (ValueError, TypeError) as error:
            status, result = HTTPStatus.BAD_REQUEST, {"error": str(error)}
        except (OSError, subprocess.SubprocessError) as error:
            status = HTTPStatus.INTERNAL_SERVER_ERROR
            result = {"error": str(error)}
        self.send_json(status, result)

    def send_json(self, status, result):
        payload = json.dumps(result, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(payload)))
        if status in (
            HTTPStatus.UNSUPPORTED_MEDIA_TYPE, HTTPStatus.NOT_ACCEPTABLE
        ):
            self.send_header("Connection", "close")
            self.close_connection = True
        self.end_headers()
        self.wfile.write(payload)


# BaseHTTPRequestHandler ищет обработчики по фиксированным именам do_METHOD.
for http_method in HTTP_METHODS:
    setattr(RequestHandler, "do_" + http_method, RequestHandler.handle_request)


def create_server(address, path, test_mode=False, command=()):
    server = ThreadingHTTPServer(address, RequestHandler)
    server.test_mode = test_mode
    server.command = command or (sys.executable, "-m", "src.ean8")
    server.generations = {}
    server.data_lock = RLock()
    server.task_pool = ThreadPoolExecutor(max_workers=1)
    server.read_data = lambda: http_store.open_store(path)
    server.write_data = lambda data: http_store.save_store(path, data)
    if not test_mode:
        for row in server.read_data()["message"]:
            if row[4] == "queued":
                server.generations[row[0]] = row
                server.task_pool.submit(complete_task, server, row)
    return server


def main():
    parser = ArgumentParser(description="HTTP API, variant 6")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--database", default="data.json")
    parser.add_argument("--test-mode", action="store_true")
    parser.add_argument(
        "--command", nargs="+", default=(sys.executable, "-m", "src.ean8")
    )
    args = parser.parse_args()
    with create_server(
        ("127.0.0.1", args.port), args.database, args.test_mode,
        args.command,
    ) as server:
        try:
            server.serve_forever()
        finally:
            server.task_pool.shutdown(wait=True)


if __name__ == "__main__":
    main()
