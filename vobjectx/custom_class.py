from functools import lru_cache

from .exceptions import VObjectError


@lru_cache(32)
def to_vname(key: str) -> str:
    key = key.removesuffix("_list")
    return key.lower().replace("-", "_")


class ContentDict(dict):
    def __getitem__(self, item):
        return super().__getitem__(to_vname(item))

    def get(self, item, default=None):
        return super().get(to_vname(item), default)

    def __setattr__(self, key, value):
        if not isinstance(value, list):
            if key.endswith("_list"):
                raise VObjectError("Component list set to a non-list")
            value = [value]

        object.__setattr__(self, to_vname(key), value)

    def __delattr__(self, key):
        object.__delattr__(self, to_vname(key))

    def setdefault(self, key, default=None, /):
        return super().setdefault(to_vname(key), default)


class Stack:
    def __init__(self):
        self.stack = []

    def __len__(self):
        return len(self.stack)

    def __bool__(self):
        return bool(self.stack)

    def top(self):
        return self.stack[-1] if self.stack else None

    def top_name(self):
        return self.stack[-1].name if self.stack else None

    def push(self, obj):
        self.stack.append(obj)

    def pop(self):
        return self.stack.pop()
