# Практическое задание №1. Вариант №6. Этап 1

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

## Запуск REPL

```text
./run.sh
```

После запуска вводим `help`.

## Структура

```text
variant6_stage1/
├── src/
│   ├── model.py
│   └── repl.py
├── .gitignore
├── README.md
└── run.sh
```
