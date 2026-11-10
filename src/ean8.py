"""Генератор EAN-8 PNG без внешних графических библиотек."""

from argparse import ArgumentParser
import json
from pathlib import Path
import struct
import zlib


LEFT = (
    "0001101", "0011001", "0010011", "0111101", "0100011",
    "0110001", "0101111", "0111011", "0110111", "0001011",
)


def normalize_code(code):
    if not isinstance(code, str) or len(code) not in (7, 8):
        raise ValueError("EAN-8 requires seven or eight ASCII digits")
    if any(char not in "0123456789" for char in code):
        raise ValueError("EAN-8 requires ASCII digits")
    total = sum(int(char) * (3 if index % 2 == 0 else 1)
                for index, char in enumerate(code[:7]))
    digit = str(-total % 10)
    if len(code) == 8 and code[-1] != digit:
        raise ValueError("Invalid EAN-8 check digit")
    return code[:7] + digit


def png_chunk(kind, data):
    checksum = zlib.crc32(kind + data)
    return (struct.pack(">I", len(data)) + kind + data
            + struct.pack(">I", checksum))


def generate_png(code):
    code = normalize_code(code)
    left = "".join(LEFT[int(char)] for char in code[:4])
    right = "".join(LEFT[int(char)] for char in code[4:])
    right = right.translate(str.maketrans("01", "10"))
    modules = "0" * 7 + "101" + left + "01010" + right + "101" + "0" * 7
    row = bytes(0 if bit == "1" else 255 for bit in modules for _ in range(3))
    width, height = len(row), 180
    pixels = (b"\x00" + row) * height
    header = struct.pack(">IIBBBBB", width, height, 8, 0, 0, 0, 0)
    return (b"\x89PNG\r\n\x1a\n" + png_chunk(b"IHDR", header)
            + png_chunk(b"IDAT", zlib.compress(pixels))
            + png_chunk(b"IEND", b""))


def main():
    parser = ArgumentParser(description="Generate an EAN-8 PNG")
    parser.add_argument("input", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    try:
        payload = json.loads(args.input.read_text(encoding="utf-8"))
        result = generate_png(payload["code"])
        args.output.write_bytes(result)
    except (OSError, ValueError, TypeError, KeyError) as error:
        parser.exit(1, str(error) + "\n")


if __name__ == "__main__":
    main()
