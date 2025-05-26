import datetime as dt

from .exceptions import ParseError
from .helper.imports_ import re


def string_to_durations(s: str) -> list:
    interval_map = {"W": "weeks", "D": "days", "H": "hours", "M": "minutes", "S": "seconds"}

    def parse_duration(duration: str):
        _sign = -1 if duration[0] == "-" else 1
        params = {}
        for part in re.findall(r"\d{0,2}[PTWDHMS]{0,2}", duration):
            if part and part[-1] in interval_map:
                params[interval_map[part[-1]]] = int(part[:-1])
        if not params:
            raise ParseError(f"Invalid duration string : {duration}")
        return _sign * dt.timedelta(**params)

    return [parse_duration(x.strip()) for x in s.strip().split(",")]
