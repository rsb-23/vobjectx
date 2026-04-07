import datetime as dt

from .constants_tmp import UTC_TZ
from .imports_ import Any
from .parser import tzinfo_eq
from .time_funcs import split_delta


# ------------------------ Serializing helper functions ------------------------
def timedelta_to_string(delta) -> str:
    """
    Convert timedelta to an ical DURATION format: PnYnMnDTnHnMnS
    """
    sign = "-" if delta.days < 0 else ""
    days, hours, minutes, seconds = split_delta(abs(delta))

    output = f"{sign}P"
    if days:
        output += f"{days}D"
    if hours or minutes or seconds:
        output += "T"
    elif not days:  # Deal with zero duration
        output += "T0S"
    if hours:
        output += f"{hours}H"
    if minutes:
        output += f"{minutes}M"
    if seconds:
        output += f"{seconds}S"
    return output


def time_to_string(date_or_date_time) -> str | Any:
    """
    Wraps date_to_string and datetime_to_string, returning the results of either based on the type of the argument
    """
    if hasattr(date_or_date_time, "hour"):
        return datetime_to_string(date_or_date_time)
    return date_to_string(date_or_date_time)


def date_to_string(date) -> Any:
    return date.strftime("%Y%m%d")


def datetime_to_string(date_time, convert_to_utc=False) -> str:
    """
    Ignore tzinfo unless convert_to_utc. Output string.
    """
    if date_time.tzinfo and convert_to_utc:
        date_time = date_time.astimezone(UTC_TZ)

    datestr = date_time.strftime("%Y%m%dT%H%M%S")
    if tzinfo_eq(date_time.tzinfo, UTC_TZ):
        datestr += "Z"
    return datestr


def delta_to_offset(delta: dt.timedelta) -> str:
    """Returns offset in format : ±HHMM"""
    # Remark : This code assumes day difference = 0
    abs_delta = split_delta(abs(delta))
    assert abs_delta.days == 0, "rethink this function uses"
    sign_string = "-" if delta.days == -1 else "+"
    return f"{sign_string}{abs_delta.hours:02}{abs_delta.minutes:02}"


def period_to_string(period, convert_to_utc=False) -> str:
    txtstart = datetime_to_string(period[0], convert_to_utc)
    if isinstance(period[1], dt.timedelta):
        txtend = timedelta_to_string(period[1])
    else:
        txtend = datetime_to_string(period[1], convert_to_utc)
    return f"{txtstart}/{txtend}"
