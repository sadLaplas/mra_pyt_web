"""Файловая модель HTTP API. Публичные записи представлены кортежами."""

import json
import os
from pathlib import Path
from time import time

USER_TYPES = (int, int, str)
MESSAGE_TYPES = (int, int, str, int, str, int)


def validate_record(record, field_types):
    if not isinstance(record, tuple) or len(record) != len(field_types):
        raise ValueError("Некорректная структура записи")
    for value, expected_type in zip(record, field_types):
        if type(value) is not expected_type:
            raise ValueError("Неверный тип поля")


def open_store(path):
    path = Path(path)
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return {"user": [], "message": [], "output": []}


def save_store(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(data, ensure_ascii=False), encoding="utf-8"
    )
    os.replace(temporary, path)


def find_records(data, table, filters):
    fields = {
        "user": ("key", "timestamp", "platform"),
        "message": ("key", "timestamp", "data", "user", "stage", "enqueued"),
        "output": ("key", "timestamp", "response", "stage", "error",
                   "message", "cache_hit"),
    }[table]
    if not isinstance(filters, dict) or set(filters) - set(fields):
        raise ValueError("Unknown search fields")
    return tuple(
        tuple(row) for row in data[table]
        if all(row[fields.index(name)] == value
               for name, value in filters.items())
    )


def make_record(data, table, record):
    types = USER_TYPES if table == "user" else MESSAGE_TYPES
    validate_record(record, types)
    if any(row[0] == record[0] for row in data[table]):
        raise ValueError("Duplicate key")
    if table == "message" and not any(
        row[0] == record[3] for row in data["user"]
    ):
        raise ValueError("User does not exist")
    data[table].append(record)
    return record


def pop_record(data, table, key):
    if table == "user" and any(row[3] == key for row in data["message"]):
        raise ValueError("User has messages")
    for index, row in enumerate(data[table]):
        if row[0] == key:
            result = data[table].pop(index)
            if table == "message":
                data["output"] = [
                    row for row in data["output"] if row[5] != key
                ]
            return tuple(result)
    raise ValueError("Record does not exist")


def report(data, now=None):
    cutoff = (int(time()) if now is None else now) - 300
    users = {row[0]: row for row in data["user"]}
    result = []
    for message in data["message"]:
        user = users.get(message[3], (None, None, None))
        for output in data["output"]:
            if message[0] == output[5]:
                if user[1] is not None and user[1] > cutoff:
                    result.append((message[2], output[2], user[2]))
    return tuple(dict.fromkeys(result))
