"""Клиент восьми обработчиков варианта 6."""

import json
from http.client import HTTPConnection
from http import HTTPStatus
from io import BytesIO
from urllib.error import HTTPError
from urllib.parse import urlsplit


class HTTPClient:
    def __init__(self, address):
        self.address = address.rstrip("/")
        parsed = urlsplit(self.address)
        self.connection = HTTPConnection(
            parsed.hostname, parsed.port, timeout=10
        )

    def request(self, method, route, body=None):
        payload = None if body is None else json.dumps(body).encode("utf-8")
        self.connection.request(
            method, "/private/api/" + route, body=payload,
            headers={"Content-Type": "application/json",
                     "Accept-Language": "en"},
        )
        response = self.connection.getresponse()
        content = response.read()
        if response.status != HTTPStatus.OK:
            raise HTTPError(
                self.address, response.status, response.reason,
                response.headers, BytesIO(content),
            )
        return json.loads(content)

    def close(self):
        self.connection.close()

    def make_user(self, record):
        return self.request("POST", "user/make", record)

    def pop_user(self, key):
        return self.request("DELETE", f"user/pop/{key}")

    def all_user(self, filters=None):
        return self.request("POST", "user/all", filters or {})

    def make_message(self, record):
        return self.request("POST", "message/make", record)

    def pop_message(self, key):
        return self.request("DELETE", f"message/pop/{key}")

    def all_message(self, user, filters=None):
        return self.request("POST", f"message/all/{user}", filters or {})

    def all_output(self, message, filters=None):
        return self.request("POST", f"output/all/{message}", filters or {})

    def all_report(self):
        return self.request("POST", "report/all", {})
