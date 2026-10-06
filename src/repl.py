"""Интерактивный вызов десяти функций модели с литералами Python."""

from ast import literal_eval

from .model import FUNCTIONS


def print_help():
    """Показать имена функций и формат передачи аргументов."""
    print("Команды: help, exit и функции модели:")
    for function in FUNCTIONS:
        print(" ", function.__name__)
    print("Пример: create_user (1, 1000, 'web')")
    print("Пример: delete_user 1")
    print("Пример: recent_messages_with_outputs 1000")


def execute_command(command):
    """Выполнить команду без исполнения произвольного Python-кода."""
    name, _, text = command.partition(" ")
    functions = {function.__name__: function for function in FUNCTIONS}
    function = functions.get(name)
    if function is None:
        raise ValueError("Неизвестная команда")
    arguments = (literal_eval(text.strip()),) if text.strip() else ()
    return function(*arguments)


def run_repl():
    """Читать команды до exit или завершения стандартного ввода."""
    print_help()
    while True:
        try:
            command = input("> ").strip()
            if command == "exit":
                return
            if command == "help":
                print_help()
            elif command:
                print(execute_command(command))
        except EOFError:
            return
        except (ValueError, TypeError, SyntaxError) as error:
            print("Ошибка:", error)
