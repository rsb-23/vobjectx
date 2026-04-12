"""List of all common imports except __future__ and aliases"""

import base64
import contextlib
import copy
import sys
from functools import lru_cache, partial
from typing import Any, Callable, Iterable, Iterator, TextIO

if sys.version_info >= (3, 11):
    from typing import Self
else:
    from typing_extensions import Self

# fmt: off
__all__ = [
    "base64", "contextlib", "copy", "sys",
    "lru_cache", "partial",
    "Any", "Callable", "Iterable", "Iterator", "Self", "TextIO",
]
# fmt: on
