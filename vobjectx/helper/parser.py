import datetime as dt

from ..exceptions import AllException
from .constants_tmp import TRANSITIONS
from .imports_ import Any, Callable, Generator, contextlib

CheckFunc = Callable[[dt.datetime], bool]


def get_transition(transition_to: str, year: int, tzinfo: dt.tzinfo) -> dt.datetime | None:
    """
    Return the datetime of the transition to/from DST, or None.
    """

    def first_transition(iter_dates, test_func: CheckFunc) -> dt.datetime:
        """
        Return the last date not matching test, or None if all tests matched.
        """
        success = None
        for _dt in iter_dates:
            if not test_func(_dt):
                success = _dt
            else:
                if success is not None:
                    return success
        return success  # may be None

    def generate_dates(year_: int, month_: int = None, day_: int = None) -> Generator[dt.datetime, Any, None]:
        """
        Iterate over possible dates with unspecified values.
        """
        months = range(1, 13)
        days = range(1, 32)
        hours = range(24)
        if month_ is None:
            for _month in months:
                yield dt.datetime(year_, _month, 1)
        elif day_ is None:
            for _day in days:
                with contextlib.suppress(ValueError):
                    yield dt.datetime(year_, month_, _day)
        else:
            for hour in hours:
                yield dt.datetime(year_, month_, day_, hour)

    assert transition_to in TRANSITIONS

    def test(dt_: dt.datetime) -> bool:
        is_standard_transition = transition_to == "standard"
        is_daylight_transition = not is_standard_transition

        # Detect Ambiguity (Overlap)
        if tzinfo.dst(dt_.replace(fold=0)) != tzinfo.dst(dt_.replace(fold=1)):
            return is_standard_transition

        # Detect Gap (Non-existent)
        dt_no_tz = dt_.replace(tzinfo=None)
        try:
            offset = tzinfo.utcoffset(dt_.replace(fold=0))
            if offset is not None:
                dt_utc = (dt_no_tz - offset).replace(tzinfo=dt.timezone.utc)
                dt_back = dt_utc.astimezone(tzinfo)
                if dt_back.replace(tzinfo=None) != dt_no_tz:
                    return is_daylight_transition
        except AllException:
            pass

        is_dt_zerodelta = tzinfo.dst(dt_) == dt.timedelta(0)
        return is_dt_zerodelta if is_standard_transition else not is_dt_zerodelta

    month_dt = first_transition(generate_dates(year), test)
    if month_dt is None:
        return dt.datetime(year, 1, 1)  # new year
    if month_dt.month == 12:
        return None

    # there was a good transition somewhere in a non-December month
    month = month_dt.month
    day = first_transition(generate_dates(year, month), test).day
    uncorrected = first_transition(generate_dates(year, month, day), test)
    if transition_to == "standard":
        # assuming tzinfo.dst returns a new offset for the first possible hour, we need to add one hour for the
        # offset change and another hour because first_transition returns the hour before the transition
        return uncorrected + dt.timedelta(hours=2)

    # Detect Gap (Non-existent) at uncorrected + 1 hour
    # Note: first_transition for daylight returns the hour before it becomes daylight.
    # In zoneinfo, this uncorrected+1 might already be 03:00 if 02:00 was skipped.
    check_dt = uncorrected + dt.timedelta(hours=1)
    is_gap = False
    try:
        # Check if uncorrected + 1 hour is a non-existent time
        # In zoneinfo, if check_dt was 02:00, and 02:00 is skipped,
        # it might already show up as something else or we can check with fold.
        # A better way to detect gap is to see if fold=0 and fold=1 result in same UTC but different wall clock
        # OR just check if it was supposed to be uncorrected + 1 but the library moved it.

        # If we are looking for daylight transition, we expect the offset to change.
        tzinfo.utcoffset(check_dt.replace(fold=0))
        tzinfo.utcoffset(check_dt.replace(fold=1))

        # For a gap (Spring forward), fold=0 and fold=1 usually return the same (the 'after' offset)
        # but we can detect it by checking if it's "imaginary"
        dt_no_tz = check_dt.replace(tzinfo=None)
        # Use an offset that we know existed just before
        prev_offset = tzinfo.utcoffset((check_dt - dt.timedelta(hours=1)).replace(fold=0))
        dt_utc_supposed = (dt_no_tz - prev_offset).replace(tzinfo=dt.timezone.utc)
        dt_actual = dt_utc_supposed.astimezone(tzinfo)
        if dt_actual.replace(tzinfo=None) != dt_no_tz:
            is_gap = True
    except AllException:
        pass

    # For daylight (Spring forward), if it's a gap, pytz used to return the start of the gap.
    # zoneinfo's get_transition logic (via fold) might find the end of the gap.
    # If we found a gap, return the hour before the gap ends (which is the hour it starts).
    if is_gap:
        return check_dt - dt.timedelta(hours=1)

    return check_dt


def tzinfo_eq(tzinfo1: dt.tzinfo, tzinfo2: dt.tzinfo, start_year: int = 2000, end_year: int = 2020) -> bool:
    """
    Compare offsets and DST transitions from start_year to end_year.
    """
    if tzinfo1 == tzinfo2:
        return True
    if tzinfo1 is None or tzinfo2 is None:
        return False

    def dt_test(_dt):
        if _dt is None:
            return True
        return tzinfo1.utcoffset(_dt) == tzinfo2.utcoffset(_dt)

    if not dt_test(dt.datetime(start_year, 1, 1)):
        return False
    for year in range(start_year, end_year):
        for transition_to in TRANSITIONS:
            t1 = get_transition(transition_to, year, tzinfo1)
            t2 = get_transition(transition_to, year, tzinfo2)
            if t1 != t2 or not dt_test(t1):
                return False
    return True
