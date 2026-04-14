import datetime as dt
from dataclasses import dataclass

from dateutil.tz import gettz

from .constants_tmp import TRANSITIONS
from .imports_ import Callable, Iterator
from .time_funcs import get_tzid

CheckFunc = Callable[[dt.datetime], bool]
DateIter = Iterator[dt.datetime]

EPOCH = dt.datetime(1970, 1, 1, tzinfo=dt.timezone.utc)


@dataclass
class Transition:
    transition_dt: dt.datetime
    offset: int
    is_standard: bool

    def __eq__(self, other) -> bool:
        return self.transition_dt == other.transition_dt and self.offset == other.offset


def get_transistions(tzinfo: dt.tzinfo, start_year=1900, end_year=2030) -> list[Transition]:
    new_year = dt.datetime(end_year, 1, 1)
    _tzid = get_tzid(tzinfo)
    if _tzid in ("UTC", None):
        return [Transition(new_year, 0, True)]

    _tz = gettz(_tzid)
    if _tz is None:
        return [Transition(new_year, 1, True)]
    transistions = []

    for ts, idx in zip(_tz._trans_list, _tz._trans_idx):  # pylint: disable=protected-access
        transistion_date = EPOCH + dt.timedelta(seconds=ts)
        if start_year <= transistion_date.year <= end_year:
            # Use dstoffset to determine if this is standard time
            # dstoffset=0 means standard time, dstoffset>0 means daylight time
            is_standard = idx.dstoffset == dt.timedelta(0)
            transistions.append(Transition(transistion_date, offset=idx.offset, is_standard=is_standard))

    return transistions


def get_transition(transition_to: str, year: int, tzinfo: dt.tzinfo) -> dt.datetime | None:
    """
    Return the datetime of the transition to/from DST, or None.

    Returns the transition time as a naive datetime in local wall-clock time,
    typically at 2:00 AM for most timezones.
    """
    assert transition_to in TRANSITIONS

    # Get transitions for the specified year
    transitions = get_transistions(tzinfo, start_year=year, end_year=year)

    # Filter transitions based on the requested type
    for trans in transitions:
        is_standard = trans.is_standard
        if (transition_to == "standard" and is_standard) or (transition_to == "daylight" and not is_standard):
            # Use the UTC transition date directly, since transitions occur at
            # a specific instant that corresponds to 2:00 AM local time
            utc_dt = trans.transition_dt
            return dt.datetime(utc_dt.year, utc_dt.month, utc_dt.day, 2, 0, 0)

    # No transition found
    return None


def tzinfo_eq(tzinfo1: dt.tzinfo, tzinfo2: dt.tzinfo, start_year: int = 1950, end_year: int = 2030) -> bool:
    """Compare offsets and DST transitions from start_year to end_year."""
    if tzinfo1 == tzinfo2:
        return True
    if tzinfo1 is None or tzinfo2 is None:
        return False

    t1_transitions = get_transistions(tzinfo1, start_year, end_year)
    t2_transitions = get_transistions(tzinfo2, start_year, end_year)

    for t1, t2 in zip(t1_transitions, t2_transitions):
        if t1 != t2:
            return False

    return True
