import datetime as dt

import pytz

from .constants_tmp import TRANSITIONS
from .imports_ import contextlib


def get_transition(transition_to, year, tzinfo):
    """
    Return the datetime of the transition to/from DST, or None.
    """

    def first_transition(iter_dates, test_func):
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

    def generate_dates(year_, month_=None, day_=None):
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

    def test(dt_):
        is_standard_transition = transition_to == "standard"
        is_daylight_transition = not is_standard_transition
        try:
            is_dt_zerodelta = tzinfo.dst(dt_) == dt.timedelta(0)
            return is_dt_zerodelta if is_standard_transition else not is_dt_zerodelta
        except pytz.NonExistentTimeError:
            return is_daylight_transition  # entering daylight time
        except pytz.AmbiguousTimeError:
            return is_standard_transition  # entering standard time

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

    return uncorrected + dt.timedelta(hours=1)


def tzinfo_eq(tzinfo1, tzinfo2, start_year=2000, end_year=2020):
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
