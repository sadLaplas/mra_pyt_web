# Практическое задание №1. Вариант №6

## Назначение

Реализована модель слоя доступа к данным, работающая с
данными в оперативной памяти.

## Публичные функции модели

Реализовано 10 функций:

- `create_user`
- `delete_user`
- `get_users`
- `create_message`
- `delete_message`
- `get_messages`
- `create_output`
- `delete_output`
- `get_outputs`
- `recent_messages_with_outputs`

Последняя функция реализует выборку по формуле реляционной алгебры из
условия варианта №6.

## Этап 1. Запуск REPL

```text
./run.sh
```

После запуска вводим `help`.

## Этап 2. RPC по TCP

Реализован TCP RPC для всех 10 функций модели. Структура запроса и ответа:
размер XML-тела — 4 байта, код операции — 2 байта, порядок байт — от
младшего к старшему.

Для запуска сервера:

```text
./run_server.sh
```

В другом терминале для демонстрации удалённых вызовов всех функций:

```text
./run_demo.sh
```

## Структура

```text
variant6/
├── src/
│   ├── model.py
│   ├── repl.py
│   ├── rpc_client.py
│   ├── rpc_demo.py
│   └── rpc_server.py
├── .gitignore
├── README.md
├── run_demo.sh
├── run_server.sh
└── run.sh
```
