import datetime as dt
from dataclasses import dataclass


@dataclass
class SimpleDelta:
    days: int
    hours: int
    minutes: int
    seconds: int

    def __iter__(self):
        yield from (self.days, self.hours, self.minutes, self.seconds)


def split_delta(delta: dt.timedelta) -> SimpleDelta:
    hours, seconds = divmod(delta.seconds, 3600)
    minutes, seconds = divmod(seconds, 60)
    return SimpleDelta(days=delta.days, hours=hours, minutes=minutes, seconds=seconds)
