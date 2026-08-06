import datetime as dt
from functools import singledispatch

from .constants_tmp import UTC_TZ
from .parser import tzinfo_eq
from .time_funcs import split_delta


# ------------------------ Serializing helper functions ------------------------
@singledispatch
def to_string(value, *args, **kwargs) -> str:
    raise TypeError(f"to_string() not implemented for type {type(value)!r}")


@to_string.register
def _(value: str, sep=" ") -> str:
    return value


@to_string.register
def _(delta: dt.timedelta) -> str:
    """Convert timedelta to an ical DURATION format: PnYnMnDTnHnMnS"""
    sign = "-" if delta.days < 0 else ""
    days, hours, minutes, seconds = split_delta(abs(delta))
    parts = [f"{sign}P"]
    if days:
        parts.append(f"{days}D")
    if hours or minutes or seconds:
        parts.append("T")
        if hours:
            parts.append(f"{hours}H")
        if minutes:
            parts.append(f"{minutes}M")
        if seconds:
            parts.append(f"{seconds}S")
    elif not days:  # Deal with zero duration
        parts.append("T0S")

    return "".join(parts)


@to_string.register
def _(date_time: dt.datetime, convert_to_utc=False) -> str:
    """Ignore tzinfo unless convert_to_utc. Output string."""
    if date_time.tzinfo and convert_to_utc:
        date_time = date_time.astimezone(UTC_TZ)

    datestr = date_time.strftime("%Y%m%dT%H%M%S")
    if tzinfo_eq(date_time.tzinfo, UTC_TZ):
        datestr += "Z"
    return datestr


@to_string.register
def _(date: dt.date) -> str:
    return date.strftime("%Y%m%d")


@to_string.register(tuple)
@to_string.register(list)
def _(value, *, convert_to_utc: bool = False, sep=" ") -> str:
    """A period is a (datetime, timedelta|datetime) pair; anything else joins with sep."""
    if len(value) != 2 or not isinstance(value[0], dt.date):
        return sep.join(value)

    txtstart = to_string(value[0], convert_to_utc)
    if isinstance(value[1], dt.timedelta):
        txtend = to_string(value[1])
    else:
        txtend = to_string(value[1], convert_to_utc)
    return f"{txtstart}/{txtend}"


def delta_to_offset(delta: dt.timedelta) -> str:
    """Returns offset in format : ±HHMM"""
    # Remark : This code assumes day difference = 0
    abs_delta = split_delta(abs(delta))
    assert abs_delta.days == 0, "rethink this function uses"
    sign_string = "-" if delta.days == -1 else "+"
    return f"{sign_string}{abs_delta.hours:02}{abs_delta.minutes:02}"
