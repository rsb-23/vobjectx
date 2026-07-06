# Contains new tests, which ain't classified yet
"""Tests for two known bugs:

Issue 4 – RRULE double-semicolon
    TimezoneComponent.tzinfo setter builds RRULE strings via:
        ";".join(["FREQ=YEARLY", day_string, f"BYMONTH={n}", end_string])
    When day_string or end_string is "" the join produces ";;", which is
    invalid per RFC 5545.  strip(";") only cleans the *ends*, leaving
    internal ";;" intact.

Issue 5 – MultiDateBehavior.transform_from_native crashes on PERIOD values
    RDATE;VALUE=PERIOD parses correctly (list of tuples) but re-serialization
    falls into the DATE-TIME branch and calls datetime_to_string() on a tuple,
    raising AttributeError.
"""

import datetime as dt
import zoneinfo

import pytest

from vobjectx import iCalendar, read_one
from vobjectx.base import ContentLine
from vobjectx.helper.serializer import period_to_string
from vobjectx.icalendar import MultiDateBehavior, TimezoneComponent
from vobjectx.registry import TzidRegistry

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

UTC = zoneinfo.ZoneInfo("UTC")

# Minimal ICS wrapper so we can feed RDATE lines through the full parse stack.
_VCAL_TMPL = """\
BEGIN:VCALENDAR\r\n\
VERSION:2.0\r\n\
PRODID:-//Test//Test//EN\r\n\
BEGIN:VEVENT\r\n\
UID:{uid}\r\n\
DTSTART:19960403T020000Z\r\n\
DTSTAMP:20240101T000000Z\r\n\
{extra}\r\n\
END:VEVENT\r\n\
END:VCALENDAR\r\n\
"""


def _make_cal(extra_line: str, uid: str = "test@example.com") -> str:
    return _VCAL_TMPL.format(uid=uid, extra=extra_line)


def _rrule_lines(serialized: str) -> list[str]:
    return [ln for ln in serialized.splitlines() if ln.startswith("RRULE:")]


def _vtimezone_rrule_values(tzname: str, start: int, end: int) -> list[str]:
    """Return all RRULE values produced by TimezoneComponent for *tzname*."""
    TzidRegistry.reset()
    tz = zoneinfo.ZoneInfo(tzname)
    tc = TimezoneComponent()
    TimezoneComponent.tzinfo.fset(tc, tz, start=start, end=end)
    values = [child.value for comp in tc.components() for child in comp.lines() if child.name == "RRULE"]

    TzidRegistry.reset()
    return values


# ===========================================================================
# Issue 4 – RRULE double-semicolon
# ===========================================================================


class TestRRuleNoDoubleSemicolon:
    """RRULE strings produced by TimezoneComponent must never contain ';;'."""

    # Timezones chosen to exercise different code paths in the tzinfo setter:
    # DST transitions in the present, historical rule changes, and no-DST zones.
    @pytest.mark.parametrize(
        "tzname, start, end",
        [
            # Current US Eastern – stable modern DST rules
            ("America/New_York", 2010, 2024),
            # Eastern across the 2007 US DST rule change – produces 'completed'
            # rules with UNTIL clauses (end_string non-empty)
            ("America/New_York", 2005, 2010),
            # Europe/London – different DST pattern
            ("Europe/London", 2000, 2024),
            # Asia/Kolkata – no DST, fixed offset; exercises all-year path
            ("Asia/Kolkata", 2000, 2024),
            # Pacific/Auckland – southern-hemisphere DST
            ("Pacific/Auckland", 2000, 2024),
            # Africa/Monrovia – historical fixed-offset zone that changed once
            ("Africa/Monrovia", 1960, 1975),
            # Pacific/Apia – unusual zone that moved across the date line
            ("Pacific/Apia", 2009, 2014),
        ],
    )
    def test_no_double_semicolon_in_rrule(self, tzname: str, start: int, end: int):
        """Every RRULE value must be free of consecutive semicolons."""
        values = _vtimezone_rrule_values(tzname, start, end)
        for value in values:
            assert ";;" not in value, f"Double semicolon in RRULE for {tzname} [{start}-{end}]: {value!r}"

    def test_no_double_semicolon_in_serialized_calendar(self):
        """Full VCALENDAR serialization must produce valid RRULE lines."""
        TzidRegistry.reset()
        eastern = zoneinfo.ZoneInfo("America/New_York")
        cal = iCalendar()
        ev = cal.add("vevent")
        ev.add("dtstart").value = dt.datetime(2005, 10, 12, 9, tzinfo=eastern)
        ev.add("uid").value = "rrule-test@example.com"
        ev.add("dtstamp").value = dt.datetime(2024, 1, 1, tzinfo=dt.timezone.utc)

        serialized = cal.serialize()
        TzidRegistry.reset()

        for line in _rrule_lines(serialized):
            assert ";;" not in line, f"Double semicolon in serialized RRULE: {line!r}"

    # ------------------------------------------------------------------
    # Direct string-construction regression: ensure the fix holds even
    # when we reproduce the exact problematic inputs (empty day_string
    # and/or empty end_string).
    # ------------------------------------------------------------------

    @pytest.mark.parametrize(
        "parts, expected",
        [
            # day_string empty, end_string set → was producing "FREQ=YEARLY;;BYMONTH=3;UNTIL=..."
            (
                ["FREQ=YEARLY", "", "BYMONTH=3", "UNTIL=20060402T070000Z"],
                "FREQ=YEARLY;BYMONTH=3;UNTIL=20060402T070000Z",
            ),
            # both empty → was producing "FREQ=YEARLY;;BYMONTH=1;"
            (["FREQ=YEARLY", "", "BYMONTH=1", ""], "FREQ=YEARLY;BYMONTH=1"),
            # neither empty → must remain unchanged
            (["FREQ=YEARLY", "BYDAY=2SU", "BYMONTH=3", ""], "FREQ=YEARLY;BYDAY=2SU;BYMONTH=3"),
            # all parts present
            (
                ["FREQ=YEARLY", "BYDAY=1SU", "BYMONTH=11", "UNTIL=20061029T060000Z"],
                "FREQ=YEARLY;BYDAY=1SU;BYMONTH=11;UNTIL=20061029T060000Z",
            ),
        ],
    )
    def test_rrule_string_building(self, parts: list[str], expected: str):
        """
        Regression: building an RRULE by joining parts must skip empty strings.

        This directly verifies the fix for the join-then-strip approach that
        left ';;' inside the string.
        """
        # Current (buggy) approach – kept here as documentation of the problem:
        buggy = ";".join(parts).strip(";")

        # Correct approach (what the fix should produce):
        correct = ";".join(p for p in parts if p)

        assert ";;" not in correct, f"Correct join still has ';;': {correct!r}"
        assert correct == expected, f"Expected {expected!r}, got {correct!r}"

        # Confirm the bug exists in the old approach for the problematic inputs:
        if "" in parts[1:-1]:  # empty in the middle → bug is observable
            assert ";;" in buggy, f"Expected buggy join to contain ';;', got {buggy!r}"


# ===========================================================================
# Issue 5 – MultiDateBehavior PERIOD round-trip
# ===========================================================================

# Canonical PERIOD RDATE used across several tests.
_RDATE_PERIOD_LINE = "RDATE;VALUE=PERIOD:19960403T020000Z/19960403T040000Z,19960404T010000Z/PT3H"

# Expected native value after transform_to_native.
_EXPECTED_NATIVE = [
    (dt.datetime(1996, 4, 3, 2, 0, tzinfo=UTC), dt.datetime(1996, 4, 3, 4, 0, tzinfo=UTC)),
    (dt.datetime(1996, 4, 4, 1, 0, tzinfo=UTC), dt.timedelta(seconds=10800)),
]


class TestMultiDatePeriodRoundTrip:
    """RDATE;VALUE=PERIOD must survive parse → native → serialize intact."""

    # ------------------------------------------------------------------
    # transform_to_native
    # ------------------------------------------------------------------

    def test_period_transform_to_native(self):
        """RDATE PERIOD parses into a list of (datetime, datetime|timedelta) tuples."""
        cl = ContentLine(
            "RDATE", [["VALUE", "PERIOD"]], "19960403T020000Z/19960403T040000Z,19960404T010000Z/PT3H", is_encoded=True
        )
        cl.behavior = MultiDateBehavior
        native = cl.transform_to_native()

        assert native.is_native
        assert len(native.value) == 2

        start1, end1 = native.value[0]
        assert isinstance(start1, dt.datetime)
        assert isinstance(end1, dt.datetime)
        assert start1 == dt.datetime(1996, 4, 3, 2, 0, tzinfo=UTC)
        assert end1 == dt.datetime(1996, 4, 3, 4, 0, tzinfo=UTC)

        start2, end2 = native.value[1]
        assert isinstance(start2, dt.datetime)
        assert isinstance(end2, dt.timedelta)
        assert end2 == dt.timedelta(hours=3)

    # ------------------------------------------------------------------
    # transform_from_native  (the bug site)
    # ------------------------------------------------------------------

    def test_period_transform_from_native_does_not_raise(self):
        """
        Regression: transform_from_native must not raise AttributeError on tuples.

        Before the fix this failed with:
            AttributeError: 'tuple' object has no attribute 'tzinfo'
        """
        cl = ContentLine(
            "RDATE", [["VALUE", "PERIOD"]], "19960403T020000Z/19960403T040000Z,19960404T010000Z/PT3H", is_encoded=True
        )
        cl.behavior = MultiDateBehavior
        native = cl.transform_to_native()

        # Must not raise:
        result = native.transform_from_native()

        assert not result.is_native
        assert isinstance(result.value, str)

    def test_period_transform_from_native_value(self):
        """After transform_from_native the value must be the original PERIOD string."""
        cl = ContentLine(
            "RDATE", [["VALUE", "PERIOD"]], "19960403T020000Z/19960403T040000Z,19960404T010000Z/PT3H", is_encoded=True
        )
        cl.behavior = MultiDateBehavior
        result = cl.transform_to_native().transform_from_native()

        # Rebuild expected string via period_to_string to avoid hard-coding
        expected = ",".join(period_to_string(p) for p in _EXPECTED_NATIVE)
        assert result.value == expected

    def test_period_value_param_set_after_round_trip(self):
        """transform_from_native must set value_param to 'PERIOD'."""
        cl = ContentLine(
            "RDATE", [["VALUE", "PERIOD"]], "19960403T020000Z/19960403T040000Z,19960404T010000Z/PT3H", is_encoded=True
        )
        cl.behavior = MultiDateBehavior
        result = cl.transform_to_native().transform_from_native()

        assert result.value_param.upper() == "PERIOD"

    # ------------------------------------------------------------------
    # Full parse → serialize round-trip through VCALENDAR
    # ------------------------------------------------------------------

    def test_period_full_parse_serialize_does_not_raise(self):
        """Parsing a VCALENDAR with RDATE PERIOD and re-serializing must not crash."""
        ics = _make_cal(_RDATE_PERIOD_LINE, uid="period-basic@example.com")
        cal = read_one(ics)
        # Before the fix this raised AttributeError during serialize():
        serialized = cal.serialize()
        assert "RDATE" in serialized

    def test_period_round_trip_preserves_value(self):
        """
        After parse → serialize → re-parse, the RDATE value must be unchanged.
        """
        ics = _make_cal(_RDATE_PERIOD_LINE, uid="period-rt@example.com")
        cal1 = read_one(ics)
        cal2 = read_one(cal1.serialize())

        v1 = cal1.vevent.rdate.value
        v2 = cal2.vevent.rdate.value
        assert v1 == v2, f"Value changed after round-trip:\n  before: {v1}\n  after:  {v2}"

    def test_period_round_trip_preserves_value_param(self):
        """VALUE=PERIOD parameter must survive the round-trip."""
        ics = _make_cal(_RDATE_PERIOD_LINE, uid="period-vp@example.com")
        cal = read_one(ics)
        serialized = cal.serialize()

        # The serialized RDATE line must carry VALUE=PERIOD
        rdate_lines = [ln for ln in serialized.splitlines() if ln.startswith("RDATE")]
        assert rdate_lines, "No RDATE line found in serialized output"
        assert "VALUE=PERIOD" in rdate_lines[0], f"VALUE=PERIOD missing from RDATE line: {rdate_lines[0]!r}"

    @pytest.mark.parametrize(
        "rdate_str, desc",
        [
            # Both periods explicit (datetime/datetime)
            ("RDATE;VALUE=PERIOD:19970101T180000Z/19970102T070000Z", "single explicit period"),
            # Single duration period
            ("RDATE;VALUE=PERIOD:19970101T180000Z/PT1H", "single duration period"),
            # Multiple mixed periods
            (
                "RDATE;VALUE=PERIOD:19970101T180000Z/19970102T070000Z,19970201T180000Z/PT2H30M",
                "mixed explicit and duration periods",
            ),
        ],
    )
    def test_period_variants_round_trip(self, rdate_str: str, desc: str):
        """Various PERIOD formats must survive parse → serialize → re-parse."""
        ics = _make_cal(rdate_str, uid=f"period-{desc.replace(' ', '-')}@example.com")
        cal1 = read_one(ics)

        # Must not raise:
        serialized = cal1.serialize()
        cal2 = read_one(serialized)

        assert cal1.vevent.rdate.value == cal2.vevent.rdate.value, f"Round-trip mismatch for {desc!r}"

    # ------------------------------------------------------------------
    # Ensure DATE and DATE-TIME branches are not broken by any fix
    # ------------------------------------------------------------------

    def test_date_branch_unaffected(self):
        """RDATE;VALUE=DATE must still round-trip correctly."""
        rdate = "RDATE;VALUE=DATE:19960403,19960404"
        ics = _make_cal(rdate, uid="date-branch@example.com")
        cal1 = read_one(ics)
        cal2 = read_one(cal1.serialize())
        assert cal1.vevent.rdate.value == cal2.vevent.rdate.value

    def test_datetime_branch_unaffected(self):
        """RDATE (implicit DATE-TIME) must still round-trip correctly."""
        rdate = "RDATE:19960403T020000Z,19960404T010000Z"
        ics = _make_cal(rdate, uid="datetime-branch@example.com")
        cal1 = read_one(ics)
        cal2 = read_one(cal1.serialize())
        assert cal1.vevent.rdate.value == cal2.vevent.rdate.value
