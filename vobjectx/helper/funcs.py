import codecs
import xml.etree.ElementTree as ETree
from random import randint

from .constants import Character as Char
from .imports_ import Iterator, lru_cache


def get_random_int(max_digit=5) -> int:
    return randint(0, 10**max_digit)


def to_list(string_or_list) -> list:
    """Turn a string or array value into a list"""
    return [string_or_list] if isinstance(string_or_list, str) else string_or_list


def to_string(value, sep=" ") -> str:
    """Turn a string or array value into a string"""
    return sep.join(value) if type(value) in (list, tuple) else value


def backslash_escape(s: str) -> str:
    s = s.replace(Char.CRLF, "\n").replace(Char.CR, "\n")
    return s.translate(str.maketrans({"\\": "\\\\", ";": "\\;", ",": "\\,", "\n": "\\n"}))


@lru_cache()
def cached_print(*x):
    print(*x)


def split_by_size(text: str, byte_size: int) -> Iterator[str]:
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


def byte_decoder(text: str | bytes, encoding="base64") -> bytes:
    if isinstance(text, str):
        text = text.encode()
    return codecs.decode(text, encoding)  # noqa: ide FP


def byte_encoder(text: str | bytes, encoding="base64") -> bytes:
    if isinstance(text, str):
        text = text.encode()
    return codecs.encode(text, encoding)  # noqa


def pretty_xml(xml_str: str, indent: int) -> str:
    root = ETree.fromstring(xml_str)
    ETree.indent(root, space=" " * indent)
    return ETree.tostring(root, encoding="unicode")
