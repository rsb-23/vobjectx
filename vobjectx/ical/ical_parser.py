import datetime as dt
import re

from vobjectx.exceptions import AllException, ParseError
from vobjectx.registry import TzidRegistry


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


# intermediate file
# ----------------------- Parsing functions ------------------------------------
def is_duration(s: str) -> bool:
    return "P" in s[:2].upper()


def string_to_date(s: str) -> dt.date:
    return dt.datetime.strptime(s, "%Y%m%d").date()


def string_to_date_time(s: str, tzinfo: dt.tzinfo | None = None, strict: bool = False) -> dt.datetime:
    if not strict:
        s = s.strip()

    try:
        _datetime = dt.datetime.strptime(s[:15], "%Y%m%dT%H%M%S")
        if len(s) > 15 and s[15] == "Z":
            tzinfo = TzidRegistry.get("UTC")
    except ValueError as e:
        raise ParseError(f"'{s!s}' is not a valid DATE-TIME") from e
    year = _datetime.year or 2000

    return dt.datetime(
        year, _datetime.month, _datetime.day, _datetime.hour, _datetime.minute, _datetime.second, 0, tzinfo
    )


# DQUOTE included to work around iCal's penchant for backslash escaping it,
# although it isn't actually supposed to be escaped according to rfc2445 TEXT
ESCAPABLE_CHAR_LIST = '\\;,Nn"'


def string_to_text_values(s: str, list_separator: str = ",", char_list: str = ESCAPABLE_CHAR_LIST) -> list[str]:
    def escaped_char(ch: str) -> str:
        if ch not in char_list:
            # leave unrecognized escaped characters for later passes
            return "\\" + ch
        return "\n" if ch in "nN" else ch

    current = []
    results = []
    to_escape = False
    for char in s:
        if to_escape:
            current.append(escaped_char(char))
            to_escape = False
            continue

        if char == "\\":
            to_escape = True
        elif char == list_separator:
            current = "".join(current)
            results.append(current)
            current = []
        else:
            current.append(char)

    if current or not results:
        current = "".join(current)
        results.append(current)
    return results


def parse_dtstart(contentline, allow_signature_mismatch: bool = False) -> dt.datetime | dt.date | None:
    """
    Convert a contentline's value into a date or date-time.

    A variety of clients don't serialize dates with the appropriate VALUE parameter, so rather than failing on these
    (technically invalid) lines, if allow_signature_mismatch is True, try to parse both varieties.
    """
    tzinfo = TzidRegistry.get(getattr(contentline, "tzid_param", None))
    value_param = getattr(contentline, "value_param", "DATE-TIME").upper()
    parsed_dtstart = None
    if value_param == "DATE":
        parsed_dtstart = string_to_date(contentline.value)
    elif value_param == "DATE-TIME":
        try:
            parsed_dtstart = string_to_date_time(contentline.value, tzinfo)
        except AllException:
            if not allow_signature_mismatch:
                raise
            parsed_dtstart = string_to_date(contentline.value)
    return parsed_dtstart


def string_to_period(s: str, tzinfo: dt.tzinfo = None) -> tuple[dt.datetime, dt.datetime]:
    values = s.split("/")
    start = string_to_date_time(values[0], tzinfo)
    val_end = values[1]
    if not is_duration(val_end):
        return start, string_to_date_time(val_end, tzinfo)
    # period-start = date-time "/" dur-value
    delta = string_to_durations(val_end)[0]
    return start, delta
