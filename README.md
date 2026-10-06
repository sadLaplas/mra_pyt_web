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
