from functools import lru_cache

from .exceptions import VObjectError

# TODO: Merge ContentDict and ParamDict, they should be same


class ContentDict(dict):
    @staticmethod
    @lru_cache()
    def _to_key(attr: str) -> str:
        attr = attr.removesuffix("_list")
        return attr.upper().replace("_", "-")

    @staticmethod
    @lru_cache()
    def _to_attr(key: str) -> str:
        key = key.removesuffix("_list")
        return key.lower().replace("-", "_")

    def __getitem__(self, item):
        return super().__getitem__(self._to_attr(item))

    def get(self, item, default=None):
        return super().get(self._to_attr(item), default)

    def __setattr__(self, key, value):
        if not isinstance(value, list):
            if key.endswith("_list"):
                raise VObjectError("Component list set to a non-list")
            value = [value]

        object.__setattr__(self, self._to_attr(key), value)

    def __delattr__(self, key):
        object.__delattr__(self, self._to_attr(key))

    def setdefault(self, key, default=None, /):
        return super().setdefault(self._to_attr(key), default)


class ParamDict(dict):
    def __init__(self, **kwargs):
        super().__init__()
        for k, v in kwargs.items():
            self[self._to_key(k)] = v

    @staticmethod
    @lru_cache()
    def _to_key(attr: str) -> str:
        for suffix in ("_param", "_paramlist"):
            attr = attr.removesuffix(suffix)
        return attr.upper().replace("_", "-")

    @staticmethod
    @lru_cache()
    def _to_attr(key: str) -> str:
        for suffix in ("_param", "_paramlist"):
            key = key.removesuffix(suffix)
        return key.lower().replace("-", "_")

    # --- dict style ---
    def __contains__(self, key: str):
        return super().__contains__(self._to_key(key))

    def __delitem__(self, key):
        return super().__delitem__(self._to_key(key))

    def __getitem__(self, key):
        return super().__getitem__(self._to_key(key))

    def __setitem__(self, key, value):
        super().__setitem__(self._to_key(key), value)

    def get(self, key, default=None):
        return super().get(self._to_key(key), default)


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
