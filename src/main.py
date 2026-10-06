"""Общая точка входа: repl, server или demo."""

from argparse import ArgumentParser

from .repl import run_repl
from .rpc_demo import run_demo
from .rpc_server import HOST, PORT, run_server


def main():
    """Выбрать режим и параметры подключения из командной строки."""
    parser = ArgumentParser(description="Вариант 6: модель и TCP RPC")
    parser.add_argument(
        "mode", nargs="?", default="repl",
        choices=("repl", "server", "demo"),
    )
    parser.add_argument("--host", default=HOST)
    parser.add_argument("--port", type=int, default=PORT)
    arguments = parser.parse_args()
    if arguments.mode == "repl":
        run_repl()
    elif arguments.mode == "server":
        run_server(arguments.host, arguments.port)
    else:
        run_demo(arguments.host, arguments.port)


if __name__ == "__main__":
    main()
