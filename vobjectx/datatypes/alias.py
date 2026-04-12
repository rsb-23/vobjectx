from .time_types import Date, DateTime, Duration, Period


def duration_to_timedelta(duration: str):
    return Duration(duration).value


def string_to_date(s: str):
    return Date(s).value


def string_to_date_time(s: str, tzinfo=None, strict: bool = False):
    return DateTime(s, tzinfo, strict=strict).value


def string_to_period(s: str, tzinfo=None):
    return Period(s, tzinfo=tzinfo).value
