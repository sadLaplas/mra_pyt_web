# Практическое задание №1. Вариант 6, ИКБО-71-24

## Stage 1. Модель и REPL

Данные User, Message и Output хранятся только в памяти процесса.
Записи представлены обычными кортежами, таблицы — списками кортежей.
Данные не сохраняются на диск. Требуется Python 3.11 или новее.

| Запись | Поля кортежа по порядку |
| --- | --- |
| User | key: int, timestamp: int, platform: str |
| Message | key: int, timestamp: int, data: str, user: int, stage: str, enqueued: int |
| Output | key: int, timestamp: int, response: str, stage: str, error: str, message: int, cache_hit: int |

Ключи задаёт вызывающий код. Message.user ссылается на User.key,
Output.message — на Message.key. Повторные ключи и неверные типы
вызывают ValueError. bool не принимается вместо int.

| Публичная функция | Аргумент | Результат |
| --- | --- | --- |
| create_user | record: кортеж User | созданная запись |
| delete_user | key: ключ User | удалённая запись |
| get_users | нет | кортеж всех User |
| create_message | record: кортеж Message | созданная запись |
| delete_message | key: ключ Message | удалённая запись |
| get_messages | нет | кортеж всех Message |
| create_output | record: кортеж Output | созданная запись |
| delete_output | key: ключ Output | удалённая запись |
| get_outputs | нет | кортеж всех Output |
| recent_messages_with_outputs | now: время в секундах, необязательно | кортеж уникальных (data, response, platform) |

Нельзя удалить User с сообщениями или Message с ответами. Для удаления
связанной цепочки сначала удаляется Output, затем Message, затем User.
Удаление отсутствующей записи вызывает ValueError.

Выборка соответствует формуле на странице 22 сборника: соединение
User.key = Message.user и Message.key = Output.message, условие
User.timestamp > now - 300, проекция (Message.data, Output.response,
User.platform). Время проверяется у пользователя. Граница исключается,
одинаковые строки результата объединяются. Message без Output не попадает
в результат. Если now не передан, используется int(time()).

Сборка не требуется. Запуск на macOS/Linux:

```sh
./run.sh
```

Запуск на любой системе из корня проекта:

```sh
python3 -m src.main
```

Каждая команда принимает один литерал Python либо не принимает аргументов.
Разбор выполняется через ast.literal_eval. Команды help и exit показывают
справку и завершают работу. Пустая строка игнорируется.

Полная интерактивная демонстрация десяти функций и ошибок:

```text
create_user (1, 1000, 'web')
create_user (1, 1000, 'web')
create_user (2, 'bad', 'web')
get_users
create_message (1, 1000, 'message', 1, 'new', 1000)
get_messages
create_output (1, 1000, 'response', 'done', '', 1, 0)
get_outputs
recent_messages_with_outputs 1000
delete_user 1
delete_message 1
delete_output 1
delete_message 1
delete_user 1
delete_user 99
exit
```

Результат выборки: (('message', 'response', 'web'),).
Ошибки показываются в консоли, после них REPL продолжает работу.

Исходники: src/model.py — модель, src/repl.py — REPL,
src/main.py — точка входа. run.sh поддерживает переменную PYTHON
для выбора интерпретатора, например PYTHON=.venv/bin/python ./run.sh.

## Stage 2. TCP RPC

RPC доступен для всех десяти функций из таблицы выше. Клиент RPCClient
реализован классом согласно сборнику; сервер реализован функциями.
Классов для записей или XML нет. Методы клиента совпадают с именами
функций модели и возвращают такие же кортежи.

Спецификация таблицы 6 применяется одинаково к запросу и ответу:

| Поле | Смещение | Размер |
| --- | --- | --- |
| Размер XML-тела | 0 | 4 байта |
| Код операции | 4 | 2 байта |
| XML-тело UTF-8 | 6 | размер из заголовка |

Порядок байт little-endian. Заголовок кодируется struct.Struct('<IH').
Коды 1–10 соответствуют порядку публичных функций в таблице Stage 1.
Запрос содержит элемент arguments типа tuple. Вложенная запись также
кодируется как tuple. Числа и строки имеют типы int и str.
Строки UTF-8 имеют атрибут encoding="base64" и кодируются Base64.
Это позволяет передавать управляющие символы в корректном XML.
Декодер принимает также обычный текст в элементах str.

Успешный ответ содержит result, ошибка — error с текстом.
Клиент проверяет код операции и тип ответа. Запросы и ответы сервера
выводятся в stdout, включая ответы с ошибками.

```sh
./run.sh server
./run.sh demo
```

Эти команды запускаются в разных терминалах. Аналоги для Windows:
run.bat server и run.bat demo. Сохранены также run_server.sh и run_demo.sh.
Демонстрация использует все десять методов и показывает запрет удаления
пользователя с сообщениями. Перед демонстрацией нужен пустой сервер.

Настройки: --host (по умолчанию 127.0.0.1), --port (5000).
Оба режима принимают эти параметры, например:

```sh
./run.sh server --port 8080
./run.sh demo --port 8080
```

Таймаут соединения — 5 секунд; интервал проверки остановки сервера —
0.1 секунды. Сервер обрабатывает подключения последовательно. Тесты могут
передать run_server событие остановки и очередь ready, получающую адрес.
Порт 0 выбирает свободный порт операционной системой.

Пример клиента:

```python
from src.rpc_client import RPCClient

client = RPCClient()
user = client.create_user((1, 1000, 'web'))
assert client.get_users() == (user,)
client.delete_user(1)
```

src/rpc_server.py содержит функции receive_exactly (полное чтение TCP),
value_to_xml/value_from_xml (преобразование кортежей и скаляров), make_body
(кодирование UTF-8), execute_request (выбор функции и обработка ошибок),
handle_connection (один обмен), serve_connections (цикл), run_server
(настройка сокета). src/rpc_client.py содержит RPCClient.call и десять
методов-обёрток. src/rpc_demo.py содержит demonstrate и run_demo.
