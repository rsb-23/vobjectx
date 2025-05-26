from .exceptions import VObjectError
from .helper.converter import to_vname


class ContentDict(dict):
    def __setattr__(self, key, value):
        if isinstance(value, list):
            if key.endswith("_list"):
                key = key[:-5]
        elif key.endswith("_list"):
            raise VObjectError("Component list set to a non-list")
        else:
            value = [value]
        object.__setattr__(self, to_vname(key), value)

    def __delattr__(self, key):
        if key.endswith("_list"):
            key = key[:-5]
        object.__delattr__(self, to_vname(key))


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
