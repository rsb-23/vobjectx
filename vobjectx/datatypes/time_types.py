# pylint: disable=r0903
import datetime as dt
import re

from vobjectx.exceptions import ParseError
from vobjectx.registry import TzidRegistry


def _is_duration(s: str) -> bool:
    return "P" in s[:2].upper()


class Date:
    def __init__(self, date_: str):
        self.text = date_
        self._parse()

    def _parse(self):
        self.value: dt.date = dt.datetime.strptime(self.text, "%Y%m%d").date()


class DateTime:
    def __init__(self, date_time_: str, tzinfo: dt.tzinfo = None, strict: bool = False):
        if not strict:
            date_time_ = date_time_.strip()
        self.text = date_time_
        self.tzinfo = tzinfo
        self._parse()

    def _parse(self):
        try:
            _datetime = dt.datetime.strptime(self.text[:15], "%Y%m%dT%H%M%S")
        except ValueError as e:
            raise ParseError(f"'{self.text}' is not a valid DATE-TIME") from e

        if len(self.text) > 15 and self.text[15] == "Z":
            self.tzinfo = TzidRegistry.get("UTC")
        self.value = _datetime.replace(tzinfo=self.tzinfo)


class Duration:
    def __init__(self, duration: str):
        self.text = duration.strip()
        self.value: dt.timedelta = dt.timedelta()
        self._parse()

    def _parse(self):
        if "," in self.text:
            raise ParseError("DURATION must have a single value.")

        interval_map = {"W": "weeks", "D": "days", "H": "hours", "M": "minutes", "S": "seconds"}

        _sign = -1 if self.text[0] == "-" else 1
        params = {}
        for part in re.findall(r"\d{0,2}[PTWDHMS]{0,2}", self.text):
            if part and part[-1] in interval_map:
                params[interval_map[part[-1]]] = int(part[:-1])
        if not params:
            raise ParseError(f"Invalid duration string : {self.text}")
        self.value = _sign * dt.timedelta(**params)


class Period:
    def __init__(self, period: str, tzinfo: dt.tzinfo = None):
        self.text = period
        self.tzinfo = tzinfo

        self.is_explicit = False
        self.start_dt = None
        self.end_dt = None
        self.delta = None
        self._parse()

    def _parse(self):
        start_dt, end_dt = self.text.split("/")
        self.start_dt = DateTime(start_dt, self.tzinfo).value
        if _is_duration(end_dt):
            # period-start = date-time "/" dur-value
            self.is_explicit = False
            self.delta = Duration(end_dt).value
        else:
            # period-explicit = date-time "/" date-time
            self.is_explicit = True
            self.end_dt = DateTime(end_dt, self.tzinfo).value

    @property
    def value(self) -> tuple[dt.datetime, dt.datetime | dt.timedelta]:
        return self.start_dt, self.delta or self.end_dt


class Time:
    def __init__(self, time: str, tzinfo: dt.tzinfo = None):
        self.text = time
        self.tzinfo = tzinfo
        self._parse()

    def _parse(self):
        try:
            _time = dt.datetime.strptime(self.text[:6], "%H%M%S").time()
        except ValueError as e:
            raise ParseError(f"'{self.text}' is not a valid TIME") from e

        if len(self.text) > 6 and self.text[6] == "Z":
            self.tzinfo = TzidRegistry.get("UTC")
        self.value = _time.replace(tzinfo=self.tzinfo)
