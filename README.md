# TCP RPC-приложение

Управление записями User, Message и Output в памяти.
Записи — кортежи; данные не сохраняются на диск. Требуется Python 3.11+.

## Stage 1. Модель и REPL

| Функция | Назначение |
| --- | --- |
| `create_user(record)` | Создать пользователя |
| `delete_user(key)` | Удалить пользователя без сообщений |
| `get_users()` | Получить всех пользователей |
| `create_message(record)` | Создать сообщение существующего пользователя |
| `delete_message(key)` | Удалить сообщение без ответов |
| `get_messages()` | Получить все сообщения |
| `create_output(record)` | Создать ответ существующего сообщения |
| `delete_output(key)` | Удалить ответ |
| `get_outputs()` | Получить все ответы |
| `recent_messages_with_outputs(now=None)` | Получить уникальные (data, response, platform) при User.timestamp > now − 300 |

Порядок полей: User — `(key, timestamp, platform)`;
Message — `(key, timestamp, data, user, stage, enqueued)`;
Output — `(key, timestamp, response, stage, error, message, cache_hit)`.
Ключи, время, ссылки и cache_hit — int; остальные поля — str.
Ошибки типов, ключей и связей вызывают ValueError.
Если now не задан, используется текущее время в секундах.

Запуск: `./run.sh`. Команды REPL совпадают с именами функций.
Пример создания, чтения, ошибки повторного ключа и удаления:

```text
create_user (1, 1000, 'web')
get_users
create_user (1, 1000, 'web')
delete_user 1
exit
```

## Stage 2. TCP RPC

`RPCClient` предоставляет те же десять методов. Формат запроса и ответа:
размер тела — 4 байта, код операции — 2 байта, затем XML UTF-8;
порядок байт little-endian. Запросы и ответы выводятся в stdout.

Сервер и демонстрация всех методов запускаются в разных терминалах:

```sh
./run.sh server
./run.sh demo
```

Настройки: `--host` (127.0.0.1), `--port` (5000), таймаут соединения —
5 секунд. Интервал проверки остановки сервера — 0.1 секунды.
Переменная `PYTHON` выбирает интерпретатор для shell-скриптов.

## Stage 3. Тестирование

`RuleBasedStateMachine` из Hypothesis сравнивает RPC с эталонной моделью.
Проверяются все десять методов, ошибки, граница времени и дубликаты.

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
PYTHON=.venv/bin/python ./run_tests.sh
```

Скрипт проверяет PEP8 и сохраняет покрытие ветвей в `coverage_report.txt`.
Настройки Hypothesis: 30 сценариев, до 50 шагов, deadline=None,
derandomize=True, database=None.

На Windows: `run.bat repl`, `run.bat server`, `run.bat demo`, `run.bat test`.
