from __future__ import annotations

import codecs
from functools import lru_cache
from random import randint
from typing import Generator

from .constants import Character as Char


def get_random_int(max_digit=5) -> int:
    return randint(0, 10**max_digit)


def backslash_escape(s: str) -> str:
    s = s.replace("\\", "\\\\").replace(";", "\\;").replace(",", "\\,")
    return s.replace(Char.CRLF, "\\n").replace(Char.LF, "\\n").replace(Char.CR, "\\n")


@lru_cache()
def cached_print(*x):
    print(*x)


def indent_str(prefix: str = " ", *, level: int = 0, tabwidth: int = 3) -> str:
    return prefix * level * tabwidth


def split_by_size(text: str, byte_size: int) -> Generator:
    start = space_count = 0
    encoded = text.encode()
    total_size = len(encoded)
    while start < total_size - byte_size:
        k = byte_size - space_count + start
        while (encoded[k] & 0xC0) == 0x80:
            k -= 1
        yield f"{encoded[start:k].decode()}{Char.CRLF} "
        space_count = 1
        start = k
    yield encoded[start:].decode()


def byte_decoder(text: str | bytes, encoding="base64") -> str | bytes:
    if type(text) is str:
        text = text.encode()
    return codecs.decode(text, encoding)


def byte_encoder(text: str | bytes, encoding="base64") -> bytes:
    if type(text) is str:
        text = text.encode()
    return codecs.encode(text, encoding)
