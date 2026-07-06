import datetime as dt
import re
from dataclasses import dataclass, field

from vobjectx.exceptions import ParseError
from vobjectx.registry import TzidRegistry


def _is_duration(s: str) -> bool:
    return "P" in s[:2].upper()


@dataclass(slots=True)
class Date:
    text: str
    value: dt.date = field(init=False)

    def __post_init__(self):
        self.value: dt.date = dt.datetime.strptime(self.text, "%Y%m%d").date()


@dataclass(slots=True)
class DateTime:
    text: str
    tzinfo: dt.tzinfo | None = None
    strict: bool = False
    value: dt.datetime = field(init=False)

    def __post_init__(self):
        if not self.strict:
            self.text = self.text.strip()

        try:
            _datetime = dt.datetime.strptime(self.text[:15], "%Y%m%dT%H%M%S")
        except ValueError as e:
            raise ParseError(f"'{self.text}' is not a valid DATE-TIME") from e

        if len(self.text) > 15 and self.text[15] == "Z":
            self.tzinfo = TzidRegistry.get("UTC")
        self.value = _datetime.replace(tzinfo=self.tzinfo)


@dataclass(slots=True)
class Duration:
    text: str
    value: dt.timedelta = field(init=False)

    def __post_init__(self):
        self.text = self.text.strip()

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


@dataclass(slots=True)
class Period:
    text: str
    tzinfo: dt.tzinfo | None = None
    is_explicit: bool = field(init=False, default=False)
    start_dt: dt.datetime = field(init=False, default=None)
    end_dt: dt.datetime = field(init=False, default=None)
    delta: dt.timedelta = field(init=False, default=None)

    def __post_init__(self):
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


@dataclass(slots=True)
class Time:
    text: str
    tzinfo: dt.tzinfo | None = None
    value: dt.time = field(init=False)

    def __post_init__(self):
        try:
            _time = dt.datetime.strptime(self.text[:6], "%H%M%S").time()
        except ValueError as e:
            raise ParseError(f"'{self.text}' is not a valid TIME") from e

        if len(self.text) > 6 and self.text[6] == "Z":
            self.tzinfo = TzidRegistry.get("UTC")
        self.value = _time.replace(tzinfo=self.tzinfo)
