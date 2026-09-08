import model


def read_int(prompt):
    while True:
        try:
            return int(input(prompt))
        except ValueError:
            print("Ошибка: требуется целое число.")


def create_user():
    record = (
        read_int("key: "),
        read_int("timestamp: "),
        input("platform: "),
    )
    print("Создана запись:", model.create_user(record))


def delete_user():
    print("Удалена запись:", model.delete_user(read_int("key: ")))


def create_message():
    record = (
        read_int("key: "),
        read_int("timestamp: "),
        input("data: "),
        read_int("user: "),
        input("stage: "),
        read_int("enqueued: "),
    )
    print("Создана запись:", model.create_message(record))


def delete_message():
    print("Удалена запись:", model.delete_message(read_int("key: ")))


def create_output():
    record = (
        read_int("key: "),
        read_int("timestamp: "),
        input("response: "),
        input("stage: "),
        input("error: "),
        read_int("message: "),
        read_int("cache_hit: "),
    )
    print("Создана запись:", model.create_output(record))


def delete_output():
    print("Удалена запись:", model.delete_output(read_int("key: ")))


def print_help():
    print("Доступные команды:")
    print("  create_user, delete_user, get_users")
    print("  create_message, delete_message, get_messages")
    print("  create_output, delete_output, get_outputs")
    print("  query, help, exit")


def run_repl():
    actions = {
        "create_user": create_user,
        "delete_user": delete_user,
        "create_message": create_message,
        "delete_message": delete_message,
        "create_output": create_output,
        "delete_output": delete_output,
    }
    print("Модель доступа к данным: вариант №6")
    print("Введите help для списка команд.")

    while True:
        command = input("> ").strip()
        if command == "exit":
            print("Работа завершена.")
            return
        if command == "help":
            print_help()
            continue
        if command == "get_users":
            print(model.get_users())
            continue
        if command == "get_messages":
            print(model.get_messages())
            continue
        if command == "get_outputs":
            print(model.get_outputs())
            continue
        if command == "query":
            print(model.recent_messages_with_outputs())
            continue
        if command not in actions:
            print("Неизвестная команда. Введите help.")
            continue
        try:
            actions[command]()
        except ValueError as error:
            print("Ошибка:", error)


if __name__ == "__main__":
    run_repl()
