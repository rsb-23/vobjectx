"""
Tests for hcalendar "Human readable part could be smarter, excluding repeated data"
(hcalendar.py line 99)

The TO-DO is on the dtend display inside HCalendar.serialize.  Today it always
calls Event.human_date(human) which returns the full weekday + month + day
string regardless of how much the start date already told the reader.  The
proposed helper human_date_end(human, start) should omit whichever parts
are already present in the dtstart label:

    date objects (all-day events, human = dtend - 1 day):
        same year AND month  → day number only,          e.g. "7"
        same year, diff month → month + day,             e.g. "November  2"
        different year        → full human_date string,  e.g. "Monday, January  2"

    datetime objects (timed events, human = dtend as-is):
        same calendar day     → time only,               e.g. "17:00"
        same year AND month   → day + time,              e.g. "7, 09:00"
        otherwise             → full human_date string

The tests are written against the *proposed* interface so they act as a
failing spec today and become green once the implementation is added.

The tests also confirm that:
  • Event.human_date still behaves correctly (no regression on the base helper)
  • The current (verbose) output is what the existing code produces – this
    documents the before/after difference explicitly.
"""

import datetime as dt

import pytest

from vobjectx import read_one
from vobjectx.hcalendar import Event

ONE_DAY = dt.timedelta(days=1)
# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_vevent_date(start: str, end: str) -> Event:
    """Build an Event from all-day DTSTART/DTEND strings (YYYYMMDD)."""
    ics = (
        "BEGIN:VCALENDAR\r\nVERSION:2.0\r\nPRODID:-//T//EN\r\n"
        "BEGIN:VEVENT\r\nSUMMARY:T\r\n"
        f"DTSTART;VALUE=DATE:{start}\r\n"
        f"DTEND;VALUE=DATE:{end}\r\n"
        "UID:t@t\r\n"
        "END:VEVENT\r\nEND:VCALENDAR\r\n"
    )
    return Event(read_one(ics).vevent)


def _make_vevent_datetime(start: str, end: str) -> Event:
    """Build an Event from floating DTSTART/DTEND strings (YYYYMMDDTHHmmss)."""
    ics = (
        "BEGIN:VCALENDAR\r\nVERSION:2.0\r\nPRODID:-//T//EN\r\n"
        "BEGIN:VEVENT\r\nSUMMARY:T\r\n"
        f"DTSTART:{start}\r\n"
        f"DTEND:{end}\r\n"
        "UID:t@t\r\n"
        "END:VEVENT\r\nEND:VCALENDAR\r\n"
    )
    return Event(read_one(ics).vevent)


# ---------------------------------------------------------------------------
# 1.  Baseline – Event.human_date (must keep working exactly as before)
# ---------------------------------------------------------------------------


class TestEventHumanDateBaseline:
    """Existing Event.human_date behaviour must not change."""

    def test_date_returns_weekday_month_day(self):
        ev = _make_vevent_date("20051005", "20051008")
        assert ev.human_date(ev.dtstart) == "Wednesday, October  5"

    def test_datetime_returns_weekday_month_day_time(self):
        ev = _make_vevent_datetime("20051005T090000", "20051005T170000")
        assert ev.human_date(ev.dtstart) == "Wednesday, October  5, 09:00"

    @pytest.mark.parametrize(
        "date_str, expected",
        [("20051001", "Saturday, October  1"), ("20051031", "Monday, October 31"), ("20060101", "Sunday, January  1")],
    )
    def test_date_formats(self, date_str: str, expected: str):
        ev = _make_vevent_date(date_str, "20061231")
        d = dt.date(int(date_str[:4]), int(date_str[4:6]), int(date_str[6:]))
        assert ev.human_date(d) == expected


# ---------------------------------------------------------------------------
# 2.  Proposed human_date_end(human, start) – date (all-day) cases
# ---------------------------------------------------------------------------


class TestHumanDateEndDateCases:
    """
    For all-day events dtend is exclusive: the display value is dtend - 1 day.
    human_date_end(human, start) should suppress repeated year/month context.
    """

    def test_same_month_and_year_returns_day_only(self):
        """
        The canonical hCalendar example: Oct 5–8 should show just '7' for the end.
        """
        ev = _make_vevent_date("20051005", "20051008")
        human = ev.dtend - ONE_DAY  # Oct 7
        assert human == dt.date(2005, 10, 7)

        result = ev.human_date(human, ev.dtstart)
        assert result == "7", f"Same-month end should be day-only '7', got {result!r}"

    def test_single_day_event_end_equals_start(self):
        """dtend = dtstart + 1 day → human = dtstart, same month → day number."""
        ev = _make_vevent_date("20051005", "20051006")
        human = ev.dtend - ONE_DAY  # Oct 5 = same as dtstart
        assert human == dt.date(2005, 10, 5)

        result = ev.human_date(human, ev.dtstart)
        assert result == "5"

    def test_last_day_of_month_to_first_of_next(self):
        """dtstart Oct 31, dtend Nov 1 → human Oct 31 → same month → '31'."""
        ev = _make_vevent_date("20051031", "20051101")
        human = ev.dtend - ONE_DAY  # Oct 31
        result = ev.human_date(human, ev.dtstart)
        assert result == "31"

    def test_same_year_different_month_returns_month_and_day(self):
        """dtstart Oct 28, dtend Nov 3 → human Nov 2 → same year, diff month."""
        ev = _make_vevent_date("20051028", "20051103")
        human = ev.dtend - ONE_DAY  # Nov 2
        assert human == dt.date(2005, 11, 2)

        result = ev.human_date(human, ev.dtstart)
        # Month name + space-padded day (%B %e pattern, consistent with human_date)
        assert result == "November  2", f"Same-year cross-month end should be 'November  2', got {result!r}"

    def test_different_year_returns_full_human_date(self):
        """dtstart Dec 29, dtend Jan 3 next year → human Jan 2 → different year → full."""
        ev = _make_vevent_date("20051229", "20060103")
        human = ev.dtend - ONE_DAY  # Jan 2 2006
        assert human == dt.date(2006, 1, 2)

        result = ev.human_date(human, ev.dtstart)
        # Must include year context – same as human_date output
        assert result == ev.human_date(human), f"Different-year end should equal human_date output, got {result!r}"
        assert "January" in result and "2006" not in result  # weekday disambiguates year
        assert result == "Monday, January  2"

    @pytest.mark.parametrize(
        "start_str, end_str, human_day, expected",
        [
            # Various same-month cases: result is always just the integer day
            ("20051001", "20051003", 2, "2"),
            ("20051015", "20051020", 19, "19"),
            ("20051001", "20051031", 30, "30"),
            # Edge: leap year same month
            ("20240228", "20240302", 1, "March  1"),  # crosses Feb/Mar, same year
        ],
    )
    def test_date_parametrized(self, start_str: str, end_str: str, human_day: int, expected: str):
        ev = _make_vevent_date(start_str, end_str)
        # Compute expected human date from dtend - 1
        human = ev.dtend - ONE_DAY
        assert human.day == human_day, f"Unexpected human day: {human}"
        result = ev.human_date(human, ev.dtstart)
        assert result == expected, f"start={start_str} end={end_str}: expected {expected!r}, got {result!r}"


# ---------------------------------------------------------------------------
# 3.  Proposed human_date_end – datetime (timed) cases
# ---------------------------------------------------------------------------


class TestHumanDateEndDatetimeCases:
    """For timed events human = dtend (no day subtraction)."""

    def test_same_day_returns_time_only(self):
        """09:00–17:00 same day: dtend label should be '17:00'."""
        ev = _make_vevent_datetime("20051005T090000", "20051005T170000")
        result = ev.human_date(ev.dtend, ev.dtstart)
        assert result == "17:00", f"Same-day dtend should show time only '17:00', got {result!r}"

    def test_same_day_midnight_boundary(self):
        """09:00 to 23:59 same day → '23:59'."""
        ev = _make_vevent_datetime("20051005T090000", "20051005T235900")
        result = ev.human_date(ev.dtend, ev.dtstart)
        assert result == "23:59"

    def test_same_month_different_day_returns_day_and_time(self):
        """Oct 5 09:00 – Oct 7 09:00: same month → '7, 09:00'."""
        ev = _make_vevent_datetime("20051005T090000", "20051007T090000")
        result = ev.human_date(ev.dtend, ev.dtstart)
        assert result == "7, 09:00", f"Same-month cross-day should be '7, 09:00', got {result!r}"

    def test_different_month_returns_full_human_date(self):
        """Oct 28 – Nov 2: different month → full string."""
        ev = _make_vevent_datetime("20051028T090000", "20051102T090000")
        result = ev.human_date(ev.dtend, ev.dtstart)
        assert result == ev.human_date(ev.dtend)
        assert result == "Wednesday, November  2, 09:00"

    def test_different_year_returns_full_human_date(self):
        """Dec 29 – Jan 2: different year → full string."""
        ev = _make_vevent_datetime("20051229T090000", "20060102T090000")
        result = ev.human_date(ev.dtend, ev.dtstart)
        assert result == ev.human_date(ev.dtend)
        assert result == "Monday, January  2, 09:00"

    @pytest.mark.parametrize(
        "start_str, end_str, expected",
        [
            ("20051005T000000", "20051005T000100", "00:01"),  # 1-min same day
            ("20051005T120000", "20051005T120000", "12:00"),  # start == end (zero-duration)
            ("20051001T090000", "20051015T090000", "15, 09:00"),  # same month, day 15
            ("20051031T090000", "20051101T090000", "Tuesday, November  1, 09:00"),  # cross month
        ],
    )
    def test_datetime_parametrized(self, start_str: str, end_str: str, expected: str):
        ev = _make_vevent_datetime(start_str, end_str)
        result = ev.human_date(ev.dtend, ev.dtstart)
        assert result == expected, f"start={start_str} end={end_str}: expected {expected!r}, got {result!r}"


# ---------------------------------------------------------------------------
# 4.  Regression – human_date_end must degrade gracefully (fallback = full)
# ---------------------------------------------------------------------------


class TestHumanDateEndFallback:
    """When years differ the output must equal human_date exactly (no info lost)."""

    def test_date_fallback_is_identical_to_human_date(self):
        ev = _make_vevent_date("20051229", "20060105")
        human = ev.dtend - ONE_DAY
        assert ev.human_date(human, ev.dtstart) == ev.human_date(human)

    def test_datetime_fallback_is_identical_to_human_date(self):
        ev = _make_vevent_datetime("20051229T090000", "20060104T090000")
        assert ev.human_date(ev.dtend, ev.dtstart) == ev.human_date(ev.dtend)


# ---------------------------------------------------------------------------
# 5.  Current behaviour documentation (shows BEFORE state, all should pass)
# ---------------------------------------------------------------------------


class TestCurrentHumanDateEndBehaviour:
    """
    Documents what the code produces TODAY (before the TO-DO is resolved).
    These assertions describe the verbose current output and will need to
    be removed (or inverted) once human_date_end is implemented and wired in.
    """

    def test_current_same_month_is_verbose(self):
        """Today the Oct 5–8 event shows 'Friday, October  7' instead of '7'."""
        ev = _make_vevent_date("20051005", "20051008")
        human = ev.dtend - ONE_DAY
        assert ev.human_date(human) == "Friday, October  7"
        # The smart version would just be '7':
        assert ev.human_date(human) != "7"

    def test_current_same_day_datetime_is_verbose(self):
        """Today a same-day event shows 'Wednesday, October  5, 17:00' instead of '17:00'."""
        ev = _make_vevent_datetime("20051005T090000", "20051005T170000")
        assert ev.human_date(ev.dtend) == "Wednesday, October  5, 17:00"
        assert ev.human_date(ev.dtend) != "17:00"
