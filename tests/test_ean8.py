import json
from pathlib import Path
import struct
import subprocess
import sys
from tempfile import TemporaryDirectory
import unittest
import zlib

from hypothesis import given, strategies as st

from src.ean8 import generate_png, normalize_code


def check_png():
    @given(st.text(alphabet="0123456789", min_size=7, max_size=7))
    def check(code):
        normalized = normalize_code(code)
        assert normalize_code(normalized) == normalized
        assert sum(int(char) * (3 if index % 2 == 0 else 1)
                   for index, char in enumerate(normalized)) % 10 == 0
        png = generate_png(code)
        assert png[:8] == b"\x89PNG\r\n\x1a\n"
        assert struct.unpack(">II", png[16:24]) == (243, 180)
        size = struct.unpack(">I", png[33:37])[0]
        assert len(zlib.decompress(png[41:41 + size])) == 244 * 180
    check()


def check_cli():
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


def load_tests(loader, tests, pattern):
    return unittest.TestSuite((
        unittest.FunctionTestCase(check_png),
        unittest.FunctionTestCase(check_cli),
    ))
