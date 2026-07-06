from .exceptions import VObjectError
from .helper.imports_ import lru_cache


@lru_cache()
def _rm_suffix(key) -> str:
    for suffix in ("_list", "_param", "_paramlist"):
        key = key.removesuffix(suffix)
    return key


@lru_cache()
def _to_key(attr: str) -> str:
    attr = _rm_suffix(attr)
    return attr.upper().replace("_", "-")


@lru_cache()
def _to_attr(key: str) -> str:
    key = _rm_suffix(key)
    return key.lower().replace("-", "_")


class ContentDict(dict):
    def __init__(self, **kwargs):
        super().__init__()
        for k, v in kwargs.items():
            self[self._to_key(k)] = v

    @staticmethod
    def _to_attr(key: str) -> str:
        return _to_attr(key)

    @staticmethod
    def _to_key(key: str) -> str:
        return _to_key(key)

    # --- dict style ---
    def __contains__(self, key: str):
        return super().__contains__(self._to_key(key))

    def __delitem__(self, key):
        return super().__delitem__(self._to_key(key))

    def __getitem__(self, key):
        return super().__getitem__(self._to_key(key))

    def __setitem__(self, item, value):
        super().__setitem__(self._to_key(item), value)

    def get(self, item, default=None):
        return super().get(self._to_key(item), default)

    def setdefault(self, item, default=None, /):
        return super().setdefault(self._to_key(item), default)

    def __getattr__(self, item):
        return self[item]

    def __setattr__(self, key, value):
        if not isinstance(value, list):
            if key.endswith("_list"):
                raise VObjectError("Component list set to a non-list")
            value = [value]
        self[key] = value

    def __delattr__(self, key):
        del self[key]


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
