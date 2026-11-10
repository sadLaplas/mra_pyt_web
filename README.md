# Практическая работа №2, вариант 6 — EAN-8

Установка зависимостей — `python3 -m pip install -r requirements.txt`.

### Этап 1. Утилита

`python3 -m src.ean8 examples/ean8/01.json examples/ean8/01.png`

Вход — JSON с полем `code`, строкой из семи или восьми ASCII-цифр.
Для семи цифр вычисляется восьмая контрольная цифра, для восьми проверяется.
Результат — PNG с EAN-8, масштабом три пикселя на модуль и свободными
полями по семь модулей. Пять входов и PNG находятся в `examples/ean8`.

### Этап 2. HTTP и файловое хранилище

`python3 -m src.http_server --database data.json`

Задания выполняются последовательно в фоновом потоке через subprocess
с вызовом CLI. Запись Message возвращается сразу со стадией `queued`.
После выполнения стадия становится `done` или `failed`. Output.response
содержит PNG в Base64, Output.error — сообщение об ошибке.
`--test-mode` заменяет вычисление фиксированным ответом `test`.
При перезапуске сохранённые задания со стадией `queued` запускаются повторно.
Удаление Message удаляет связанные Output и исключает публикацию его
отложенного результата. Данные сохраняются после каждой операции.

Обязательные заголовки — `Content-Type: application/json` для POST/PUT/PATCH
и `Accept-Language: en` для всех методов. При нарушении возвращаются
415 и 406 в указанном порядке. Ошибки входных данных возвращают 400,
неизвестные маршруты — 404. Успешные ответы имеют код 200 и тело JSON.

| Метод | Маршрут | Тело |
| --- | --- | --- |
| POST | /private/api/user/make | `[key, timestamp, platform]` |
| DELETE | /private/api/user/pop/:key | — |
| POST | /private/api/user/all | объект фильтров по полям |
| POST | /private/api/message/make | `[key, timestamp, data, user, stage, enqueued]` |
| DELETE | /private/api/message/pop/:key | — |
| POST | /private/api/message/all/:user | объект фильтров |
| POST | /private/api/output/all/:message | объект фильтров |
| POST | /private/api/report/all | — |

Поле Message.data — строка JSON, например `{"code":"9638507"}`.
Имена методов `HTTPClient` соответствуют действию и таблице.

```python
import json
from time import time
from src.http_client import HTTPClient

client = HTTPClient("http://127.0.0.1:8000")
client.make_user((1, int(time()), "web"))
client.make_message((1, 0, json.dumps({"code": "9638507"}), 1, "new", 0))
print(client.all_output(1))  # Опросить повторно до появления результата.
```

Формула (6) сохраняет Message при правом внешнем соединении с User,
затем связывает Output по `Message.key = Output.message`. Фильтр использует
строго `User.timestamp > now - 300`. Сообщения без User исключаются этим
фильтром. Результат содержит уникальные `(data, response, platform)`.

### Проверка этапа 2

`PYTHON=.venv/bin/python sh run_http_tests.sh` запускает MBT для файлового
хранилища, проверку асинхронного выполнения и формулы. Все вызовы восьми
обработчиков выполняются сгенерированными Hypothesis тестами.
Покрытие ветвей сохраняется в `http_coverage_report.txt`.
Тесты генератора отдельно — `python3 -m unittest discover -s tests -p test_ean8.py`.
