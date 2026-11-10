"""Проверки контрольной цифры, структуры PNG и файлового интерфейса CLI."""

import json
from io import BytesIO
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from hypothesis import given, strategies as st
from PIL import Image

from src.ean8 import generate_png, main


def check_png():
    """Проверить читаемость PNG и эквивалентность кодов из 7 и 8 цифр."""
    @given(st.text(alphabet="0123456789", min_size=7, max_size=7))
    def check(code):
        """Проверить PNG через Pillow и контрольную цифру независимо."""
        total = sum(int(char) * (3 if index % 2 == 0 else 1)
                    for index, char in enumerate(code))
        complete = code + str(-total % 10)
        png = generate_png(code)
        assert png == generate_png(complete)
        with Image.open(BytesIO(png)) as image:
            assert image.format == "PNG"
            assert image.width > 0 and image.height > 0
            image.verify()
    check()


def check_cli():
    """Сравнить результат CLI и прямого вызова для пяти примеров."""
    with TemporaryDirectory() as directory:
        for index, code in enumerate((
            "1234567", "9638507", "5512345", "0000000", "9999999"
        )):
            source = Path(directory) / f"input{index}.json"
            target = Path(directory) / f"output{index}.png"
            source.write_text(json.dumps({"code": code}), encoding="utf-8")
            subprocess.run(
                (sys.executable, "-m", "src.ean8", str(source), str(target)),
                check=True,
            )
            assert target.read_bytes() == generate_png(code)
            with patch("sys.argv", ["ean8", str(source), str(target)]):
                main()
            assert target.read_bytes() == generate_png(code)


@given(st.sampled_from((
    "", "123456", "12345678", "１２３４５６７", "1234567x", "123456789",
    "1234567\n", None, 1234567,
)))
def check_invalid_code(code):
    """Проверить отказ для неверной длины, типа, алфавита и контрольной."""
    try:
        generate_png(code)
    except ValueError:
        pass
    else:
        raise AssertionError("Invalid code accepted")


def load_tests(loader, tests, pattern):
    """Зарегистрировать функциональные тесты в стандартном unittest."""
    return unittest.TestSuite((
        unittest.FunctionTestCase(check_png),
        unittest.FunctionTestCase(check_cli),
        unittest.FunctionTestCase(check_invalid_code),
    ))
