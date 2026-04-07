def to_list(string_or_list) -> list:
    return [string_or_list] if isinstance(string_or_list, str) else string_or_list


def to_string(value, sep=" ") -> str:
    """
    Turn a string or array value into a string.
    """
    return sep.join(value) if type(value) in (list, tuple) else value
