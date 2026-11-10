"""Генерация EAN-8 через python-barcode и запись PNG через Pillow."""

from argparse import ArgumentParser
import json
from io import BytesIO
from pathlib import Path
import re

from barcode import EAN8
from barcode.writer import ImageWriter


CODE_DIGITS = 8


def generate_png(code):
    if not isinstance(code, str) or re.fullmatch(r"[0-9]{7,8}", code) is None:
        raise ValueError("EAN-8 requires seven or eight ASCII digits")
    barcode = EAN8(code, writer=ImageWriter())
    if len(code) == CODE_DIGITS and barcode.get_fullcode() != code:
        raise ValueError("Invalid EAN-8 check digit")
    with BytesIO() as output:
        barcode.write(output, options={"format": "PNG"})
        return output.getvalue()


def main():
    """Прочитать JSON из входного файла и записать PNG по выходному пути."""
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
