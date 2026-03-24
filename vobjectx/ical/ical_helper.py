import datetime as dt
import math

# -------------------- Helper subclasses ---------------------------------------


def date_to_datetime_(dt_obj: dt.datetime | dt.date):
    if isinstance(dt_obj, dt.datetime):
        return dt_obj
    return dt.datetime.fromordinal(dt_obj.toordinal())


def from_last_week_(dt_):
    """
    How many weeks from the end of the month dt is, starting from 1.
    """
    next_month = dt.datetime(dt_.year, dt_.month + 1, 1)
    time_diff = next_month - dt_
    days_gap = time_diff.days + bool(time_diff.seconds)
    return math.ceil(days_gap / 7)
