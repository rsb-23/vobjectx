import datetime as dt
import math

from vobjectx import datatypes as vtypes
from vobjectx.exceptions import ParseError
from vobjectx.registry import TzidRegistry

# -------------------- Helper funcs ---------------------------------------


def date_to_datetime_(dt_obj: dt.datetime | dt.date) -> dt.datetime:
    if isinstance(dt_obj, dt.datetime):
        return dt_obj
    return dt.datetime.fromordinal(dt_obj.toordinal())


def from_last_week_(dt_: dt.datetime) -> int:
    """
    How many weeks from the end of the month dt is, starting from 1.
    """
    next_month = dt.datetime(dt_.year, dt_.month + 1, 1)
    time_diff = next_month - dt_
    days_gap = time_diff.days + bool(time_diff.seconds)
    return math.ceil(days_gap / 7)


# -------------------- Parser funcs ---------------------------------------

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
        parsed_dtstart = vtypes.Date(contentline.value).value
    elif value_param == "DATE-TIME":
        try:
            parsed_dtstart = vtypes.DateTime(contentline.value, tzinfo).value
        except ParseError as e:
            if not allow_signature_mismatch:
                raise e
            parsed_dtstart = vtypes.Date(contentline.value).value
    return parsed_dtstart
