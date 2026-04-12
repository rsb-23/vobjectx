from typing import Any, Protocol

from .alias import duration_to_timedelta, string_to_date, string_to_date_time, string_to_period
from .time_types import Date, DateTime, Duration, Period, Time


# pylint: disable=r0903
class DataType(Protocol):
    text: str
    value: Any

    def _parse(self):
        pass
