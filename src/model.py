from time import time

FIVE_MINUTES = 5 * 60
USERS = []
MESSAGES = []
OUTPUTS = []


def create_user(record):
    if not isinstance(record, tuple) or len(record) != 3:
        raise ValueError("User должен быть кортежем из 3 полей")
    if any(user[0] == record[0] for user in USERS):
        raise ValueError(f"User с key={record[0]} уже существует")
    USERS.append(record)
    return record


def delete_user(key):
    """Удалить запись User по ключу."""
    for index, user in enumerate(USERS):
        if user[0] == key:
            return USERS.pop(index)
    raise ValueError("User не найден")


def get_users():
    return tuple(USERS)


def create_message(record):
    if not isinstance(record, tuple) or len(record) != 6:
        raise ValueError("Message должен быть кортежем из 6 полей")
    if any(message[0] == record[0] for message in MESSAGES):
        raise ValueError(
            f"Message с key={record[0]} уже существует"
        )
    if not any(user[0] == record[3] for user in USERS):
        raise ValueError("Указанный User не существует")
    MESSAGES.append(record)
    return record


def delete_message(key):
    """Удалить запись Message по ключу."""
    for index, message in enumerate(MESSAGES):
        if message[0] == key:
            return MESSAGES.pop(index)
    raise ValueError("Message не найден")


def get_messages():
    """Получить все записи Message."""
    return tuple(MESSAGES)


def create_output(record):
    if not isinstance(record, tuple) or len(record) != 7:
        raise ValueError("Output должен быть кортежем из 7 полей")
    if any(output[0] == record[0] for output in OUTPUTS):
        raise ValueError(
            f"Output с key={record[0]} уже существует"
        )
    if not any(message[0] == record[5] for message in MESSAGES):
        raise ValueError("Указанный Message не существует")
    OUTPUTS.append(record)
    return record


def delete_output(key):
    for index, output in enumerate(OUTPUTS):
        if output[0] == key:
            return OUTPUTS.pop(index)
    raise ValueError("Output не найден")


def get_outputs():
    return tuple(OUTPUTS)


def recent_messages_with_outputs(now=None):
    current_time = int(time()) if now is None else now
    cutoff = current_time - FIVE_MINUTES
    result = []

    for user in USERS:
        if user[1] <= cutoff:
            continue
        for message in MESSAGES:
            if message[3] != user[0]:
                continue
            for output in OUTPUTS:
                if output[5] == message[0]:
                    result.append(
                        (message[2], output[2], user[2])
                    )
    return tuple(result)
