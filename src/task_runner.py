"""Запуск утилиты курсовой через файлы и subprocess."""

from base64 import b64encode
from pathlib import Path
import subprocess
from tempfile import TemporaryDirectory


def run_task(command, payload):
    if not command:
        raise ValueError("Configure the coursework CLI command")
    with TemporaryDirectory(prefix="variant6-") as directory:
        source = Path(directory) / "input.json"
        target = Path(directory) / "output.png"
        source.write_text(payload, encoding="utf-8")
        subprocess.run(
            (*command, str(source), str(target)), check=True,
            capture_output=True, text=True, timeout=60,
        )
        return b64encode(target.read_bytes()).decode("ascii")
