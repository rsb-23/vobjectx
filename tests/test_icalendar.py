import datetime as dt
import re
from random import sample

import dateutil
import pytz
from dateutil.rrule import MONTHLY, WEEKLY, rrule, rruleset
from dateutil.tz import tzutc

from vobject import base
from vobject.icalendar import (
    RecurringComponent,
    TimezoneComponent,
    VCalendar2_0,
    delta_to_offset,
    get_tzid,
    parse_dtstart,
    register_tzid,
    string_to_period,
    string_to_text_values,
    timedelta_to_string,
    utc,
)

from .common import TEST_FILE_DIR, get_test_file, two_hours


def test_parse_dtstart():
    """Should take a content line and return a datetime object."""
    assert parse_dtstart(base.text_line_to_content_line("DTSTART:20060509T000000")) == dt.datetime(  # inline
        2006, 5, 9, 0, 0
    )


def test_regexes():
    """Test regex patterns"""
    assert re.findall(base.patterns["name"], "12foo-bar:yay") == ["12foo-bar", "yay"]
    assert re.findall(base.patterns["safe_char"], 'a;b"*,cd') == ["a", "b", "*", "c", "d"]
    assert re.findall(base.patterns["qsafe_char"], 'a;b"*,cd') == ["a", ";", "b", "*", ",", "c", "d"]
    assert re.findall(
        base.patterns["param_value"], '"quoted";not-quoted;start"after-illegal-quote', re.VERBOSE  # inline
    ) == ['"quoted"', "", "not-quoted", "", "start", "", "after-illegal-quote", ""]

    match = base.line_re.match('TEST;ALTREP="http://www.wiz.org":value:;"')
    assert match.group("value") == 'value:;"'
    assert match.group("name") == "TEST"
    assert match.group("params") == ';ALTREP="http://www.wiz.org"'


def test_string_to_text_values():
    """Test string lists"""
    assert string_to_text_values(""), [""]
    assert string_to_text_values("abcd,efgh"), ["abcd", "efgh"]


def test_string_to_period():
    """Test datetime strings"""
    assert string_to_period("19970101T180000Z/19970102T070000Z") == (
        dt.datetime(1997, 1, 1, 18, 0, tzinfo=tzutc()),
        dt.datetime(1997, 1, 2, 7, 0, tzinfo=tzutc()),
    )

    assert string_to_period("19970101T180000Z/PT1H") == (
        dt.datetime(1997, 1, 1, 18, 0, tzinfo=tzutc()),
        dt.timedelta(0, 3600),
    )


def test_timedelta_to_string():
    """Test timedelta strings"""
    assert timedelta_to_string(two_hours) == "PT2H"
    assert timedelta_to_string(dt.timedelta(minutes=20)) == "PT20M"


def test_delta_to_offset():
    """Test delta_to_offset() function."""

    # Sydney
    delta = dt.timedelta(hours=10)
    assert delta_to_offset(delta) == "+1000"

    # New York
    delta = dt.timedelta(hours=-5)
    assert delta_to_offset(delta) == "-0500"

    # Adelaide (see https://github.com/py-vobject/vobject/pull/12)
    delta = dt.timedelta(hours=9, minutes=30)
    assert delta_to_offset(delta) == "+0930"


def test_vtimezone_creation():
    """Test timezones"""
    tzs = dateutil.tz.tzical(f"{TEST_FILE_DIR}/timezones.ics")
    pacific = TimezoneComponent(tzs.get("US/Pacific"))
    assert str(pacific) == "<VTIMEZONE | <TZID{}US/Pacific>>"
    santiago = TimezoneComponent(tzs.get("Santiago"))
    assert str(santiago) == "<VTIMEZONE | <TZID{}Santiago>>"
    for year in range(2001, 2010):
        for month in (2, 9):
            _dt = dt.datetime(year, month, 15, tzinfo=tzs.get("Santiago"))
            assert _dt.replace(tzinfo=tzs.get("Santiago")), _dt


def test_timezone_serializing():
    """Serializing with timezones test"""
    tzs = dateutil.tz.tzical(f"{TEST_FILE_DIR}/timezones.ics")
    pacific = tzs.get("US/Pacific")
    cal = base.Component("VCALENDAR")
    cal.set_behavior(VCalendar2_0)
    ev = cal.add("vevent")
    ev.add("dtstart").value = dt.datetime(2005, 10, 12, 9, tzinfo=pacific)
    evruleset = rruleset()
    evruleset.rrule(rrule(WEEKLY, interval=2, byweekday=[2, 4], until=dt.datetime(2005, 12, 15, 9)))
    evruleset.rrule(rrule(MONTHLY, bymonthday=[-1, -5]))
    evruleset.exdate(dt.datetime(2005, 10, 14, 9, tzinfo=pacific))
    ev.rruleset = evruleset
    ev.add("duration").value = dt.timedelta(hours=1)

    apple = tzs.get("America/Montreal")
    ev.dtstart.value = dt.datetime(2005, 10, 12, 9, tzinfo=apple)


def test_pytz_timezone_serializing():
    """Serializing with timezones from pytz test"""

    # Avoid conflicting cached tzinfo from other tests
    def unregister_tzid(tzid):
        """Clear tzid from icalendar TZID registry"""
        if get_tzid(tzid, False):
            register_tzid(tzid, tzutc())

    unregister_tzid("US/Eastern")
    eastern = pytz.timezone("US/Eastern")
    cal = base.Component("VCALENDAR")
    cal.set_behavior(VCalendar2_0)
    ev = cal.add("vevent")
    ev.add("dtstart").value = eastern.localize(dt.datetime(2008, 10, 12, 9))
    serialized = cal.serialize()

    expected_vtimezone = get_test_file("tz_us_eastern.ics")
    assert expected_vtimezone.replace("\r\n", "\n") in serialized.replace("\r\n", "\n")

    # Randomly test k zones (just looking for no errors)
    for tzname in sample(pytz.all_timezones, k=50):
        unregister_tzid(tzname)
        tz = TimezoneComponent(tzinfo=pytz.timezone(tzname))
        tz.serialize()


def _add_tags(comp, uid, dtstamp, dtstart, dtend):
    comp.add("uid").value = uid
    comp.add("dtstamp").value = dtstamp
    comp.add("dtstart").value = dtstart
    comp.add("dtend").value = dtend


def test_free_busy():
    """Test freebusy components"""
    test_cal = get_test_file("freebusy.ics")

    vfb = base.new_from_behavior("VFREEBUSY")
    _add_tags(
        vfb,
        uid="test",
        dtstamp=dt.datetime(2006, 2, 15, 0, tzinfo=utc),
        dtstart=dt.datetime(2006, 2, 16, 1, tzinfo=utc),
        dtend=None,
    )
    vfb.dtend.value = vfb.dtstart.value + two_hours
    vfb.add("freebusy").value = [(vfb.dtstart.value, two_hours / 2)]
    vfb.add("freebusy").value = [(vfb.dtstart.value, vfb.dtend.value)]

    assert vfb.serialize().replace("\r\n", "\n"), test_cal.replace("\r\n", "\n")


def test_availablity():
    """
    Test availability components
    """
    test_cal = get_test_file("availablity.ics")

    vcal = base.new_from_behavior("VAVAILABILITY")
    _add_tags(
        vcal,
        uid="test",
        dtstamp=dt.datetime(2006, 2, 15, 0, tzinfo=utc),
        dtstart=dt.datetime(2006, 2, 16, 0, tzinfo=utc),
        dtend=dt.datetime(2006, 2, 17, 0, tzinfo=utc),
    )
    vcal.add("busytype").value = "BUSY"

    av = base.new_from_behavior("AVAILABLE")
    _add_tags(
        av,
        uid="test1",
        dtstamp=dt.datetime(2006, 2, 15, 0, tzinfo=utc),
        dtstart=dt.datetime(2006, 2, 16, 9, tzinfo=utc),
        dtend=dt.datetime(2006, 2, 16, 12, tzinfo=utc),
    )
    av.add("summary").value = "Available in the morning"

    vcal.add(av)

    assert vcal.serialize().replace("\r\n", "\n"), test_cal.replace("\r\n", "\n")


def get_dates_of_first_component(arg0):
    test_file = get_test_file(arg0)
    cal = base.read_one(test_file)
    return list(cal.vevent.rruleset)


def test_recurrence():
    """
    Ensure date valued UNTILs in rrules are in a reasonable timezone, and include that day (12/28 in this test)
    """
    dates = get_dates_of_first_component("recurrence.ics")
    assert dates[0], dt.datetime(2006, 1, 26, 23, 0, tzinfo=tzutc())
    assert dates[1], dt.datetime(2006, 2, 23, 23, 0, tzinfo=tzutc())
    assert dates[-1], dt.datetime(2006, 12, 28, 23, 0, tzinfo=tzutc())


def test_recurring_component():
    """Test recurring events"""
    vevent = RecurringComponent(name="VEVENT")

    # init
    assert vevent.is_native

    # rruleset should be None at this point.
    # No rules have been passed or created.
    assert vevent.rruleset is None

    # Now add start and rule for recurring event
    vevent.add("dtstart").value = dt.datetime(2005, 1, 19, 9)
    vevent.add("rrule").value = "FREQ=WEEKLY;COUNT=2;INTERVAL=2;BYDAY=TU,TH"
    assert list(vevent.rruleset) == [dt.datetime(2005, 1, 20, 9, 0), dt.datetime(2005, 2, 1, 9, 0)]  # noqa
    assert list(vevent.getrruleset(add_rdate=True)), [dt.datetime(2005, 1, 19, 9, 0) == dt.datetime(2005, 1, 20, 9, 0)]

    # Also note that dateutil will expand all-day events (dt.date values)
    # to dt.datetime value with time 0 and no timezone.
    vevent.dtstart.value = dt.date(2005, 3, 18)
    assert list(vevent.rruleset), [dt.datetime(2005, 3, 29, 0, 0), dt.datetime(2005, 3, 31, 0, 0)]  # noqa
    assert list(vevent.getrruleset(add_rdate=True)), [dt.datetime(2005, 3, 18, 0, 0) == dt.datetime(2005, 3, 29, 0, 0)]


def _recurrence_test(file_name):
    dates = get_dates_of_first_component(file_name)
    assert dates[0] == dt.datetime(2013, 1, 17)
    assert dates[1] == dt.datetime(2013, 1, 24)
    assert dates[-1] == dt.datetime(2013, 3, 28)


def test_recurrence_without_tz():
    """Test recurring vevent missing any time zone definitions."""
    _recurrence_test("recurrence-without-tz.ics")


def test_recurrence_offset_naive():
    """Ensure recurring vevent missing some time zone definitions is parsing. See issue #75."""
    _recurrence_test("recurrence-offset-naive.ics")


def test_issue50():
    """
    Ensure leading spaces in a DATE-TIME value are ignored when not in strict mode.

    See https://github.com/py-vobject/vobject/issues/50
    """
    test_file = get_test_file("vobject_0050.ics")
    cal = base.read_one(test_file)
    assert dt.datetime(2024, 8, 12, 22, 30, tzinfo=tzutc()) == cal.vevent.dtend.value
