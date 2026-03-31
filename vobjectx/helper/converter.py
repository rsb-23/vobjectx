def to_basestring(value: str | bytes) -> bytes:
    """Converts a string argument to a byte string.

    If the argument is already a byte string, it is returned unchanged.
    Otherwise it must be a unicode string and is encoded as utf8.
    """
    return value.encode() if isinstance(value, str) else value


def to_list(string_or_list) -> list:
    return [string_or_list] if isinstance(string_or_list, str) else string_or_list


def to_string(value, sep=" ") -> str:
    """
    Turn a string or array value into a string.
    """
    return sep.join(value) if type(value) in (list, tuple) else value


def to_unicode(value: str | bytes):
    """Converts a string argument to a unicode string.

    If the argument is already a unicode string, it is returned
    unchanged.  Otherwise it must be a byte string and is decoded as utf8.
    """
    return value.decode() if isinstance(value, bytes) else value
