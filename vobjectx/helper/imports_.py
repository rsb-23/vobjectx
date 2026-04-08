"""List of all common imports except __future__ and aliases"""

import base64
import contextlib
import copy
import re
import sys
from functools import lru_cache, partial
from typing import Any, Callable, Generator, Iterable, TextIO

if sys.version_info >= (3, 11):
    from typing import Self
else:
    from typing_extensions import Self

# fmt: off
__all__ = [
    "base64", "contextlib", "copy", "re", "sys",
    "lru_cache", "partial",
    "Any", "Callable", "Generator", "Iterable", "Self", "TextIO",
]
# fmt: on
