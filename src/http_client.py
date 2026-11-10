"""Клиент восьми маршрутов HTTP API варианта 6."""

from http import HTTPStatus
from io import BytesIO
from urllib.error import HTTPError

from requests import Session


class HTTPClient:
    """Выполнять запросы API через повторно используемое HTTP-соединение."""

    def __init__(self, address):
        """Создать соединение с HTTP-сервером по его базовому URL."""
        self.address = address.rstrip("/")
        self.session = Session()
        self.session.trust_env = False
        self.session.headers.update({
            "Content-Type": "application/json", "Accept-Language": "en",
        })

    def request(self, method, route, body=None):
        """Отправить JSON с заголовками и вызвать HTTPError при отказе API."""
        with self.session.request(
            method, self.address + "/private/api/" + route,
            json=body, timeout=10, allow_redirects=False,
        ) as response:
            if response.status_code != HTTPStatus.OK:
                raise HTTPError(
                    response.url, response.status_code, response.reason,
                    response.headers, BytesIO(response.content),
                )
            return response.json()

    def close(self):
        """Закрыть клиентское соединение."""
        self.session.close()

    def make_user(self, record):
        """Создать User из (key, timestamp, platform)."""
        return self.request("POST", "user/make", record)

    def pop_user(self, key):
        """Удалить User, у которого отсутствуют сообщения."""
        return self.request("DELETE", f"user/pop/{key}")

    def all_user(self, filters=None):
        """Найти пользователей по равенству указанных полей."""
        return self.request("POST", "user/all", filters or {})

    def make_message(self, record):
        """Создать Message и поставить генерацию штрихкода в очередь."""
        return self.request("POST", "message/make", record)

    def pop_message(self, key):
        """Удалить Message и связанные результаты Output."""
        return self.request("DELETE", f"message/pop/{key}")

    def all_message(self, user, filters=None):
        """Найти сообщения указанного пользователя с учётом фильтров."""
        return self.request("POST", f"message/all/{user}", filters or {})

    def all_output(self, message, filters=None):
        """Найти результаты указанного сообщения с учётом фильтров."""
        return self.request("POST", f"output/all/{message}", filters or {})

    def all_report(self):
        """Получить уникальные тройки отчёта по формуле варианта 6."""
        return self.request("POST", "report/all", {})
