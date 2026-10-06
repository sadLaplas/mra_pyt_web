from time import time

FIVE_MINUTES = 5 * 60
USERS = []
MESSAGES = []
OUTPUTS = []
USER_TYPES = (int, int, str)
MESSAGE_TYPES = (int, int, str, int, str, int)
OUTPUT_TYPES = (int, int, str, str, str, int, int)


def validate_record(record, field_types):
    if not isinstance(record, tuple) or len(record) != len(field_types):
        raise ValueError("Некорректная структура записи")
    for index, expected_type in enumerate(field_types):
        if type(record[index]) is not expected_type:
            raise ValueError("Неверный тип поля")


def create_user(record):
    validate_record(record, USER_TYPES)
    if any(user[0] == record[0] for user in USERS):
        raise ValueError("Ключ User уже существует")
    USERS.append(record)
    return record


def delete_user(key):
    if any(message[3] == key for message in MESSAGES):
        raise ValueError("У User есть сообщения")
    for index, user in enumerate(USERS):
        if user[0] == key:
            return USERS.pop(index)
    raise ValueError("User не найден")


def get_users():
    return tuple(USERS)


def create_message(record):
    validate_record(record, MESSAGE_TYPES)
    if any(message[0] == record[0] for message in MESSAGES):
        raise ValueError(
            f"Message с key={record[0]} уже существует"
        )
    if not any(user[0] == record[3] for user in USERS):
        raise ValueError("Указанный User не существует")
    MESSAGES.append(record)
    return record


def delete_message(key):
    if any(output[5] == key for output in OUTPUTS):
        raise ValueError("У Message есть ответы")
    for index, message in enumerate(MESSAGES):
        if message[0] == key:
            return MESSAGES.pop(index)
    raise ValueError("Message не найден")


def get_messages():
    """Получить все записи Message."""
    return tuple(MESSAGES)


def create_output(record):
    validate_record(record, OUTPUT_TYPES)
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
    return tuple(dict.fromkeys(result))


FUNCTIONS = (
    create_user,
    delete_user,
    get_users,
    create_message,
    delete_message,
    get_messages,
    create_output,
    delete_output,
    get_outputs,
    recent_messages_with_outputs,
)
