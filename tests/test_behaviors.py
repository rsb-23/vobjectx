import datetime as dt

from vobject.base import ContentLine
from vobject.base import __behavior_registry as behavior_registry
from vobject.base import get_behavior, text_line_to_content_line
from vobject.icalendar import MultiDateBehavior, PeriodBehavior

from .common import two_hours


def test_general_behavior():
    """Tests for behavior registry, getting and creating a behavior."""
    # Check expected behavior registry
    # fmt: off
    assert sorted(behavior_registry.keys()) == [
        "", "ACTION", "ADR", "AVAILABLE", "BUSYTYPE", "CALSCALE", "CATEGORIES", "CLASS", "COMMENT", "COMPLETED",
        "CONTACT", "CREATED", "DAYLIGHT", "DESCRIPTION", "DTEND", "DTSTAMP", "DTSTART", "DUE", "DURATION", "EXDATE",
        "EXRULE", "FN", "FREEBUSY", "GEO", "LABEL", "LAST-MODIFIED", "LOCATION", "METHOD", "N", "ORG", "PHOTO",
        "PRODID", "RDATE", "RECURRENCE-ID", "RELATED-TO", "REQUEST-STATUS", "RESOURCES", "RRULE", "STANDARD",
        "STATUS", "SUMMARY", "TRANSP", "TRIGGER", "UID", "VALARM", "VAVAILABILITY", "VCALENDAR", "VCARD", "VEVENT",
        "VFREEBUSY", "VJOURNAL", "VTIMEZONE", "VTODO",
    ]
    # fmt: on

    # test get_behavior
    behavior = get_behavior("VCALENDAR")
    assert str(behavior) == "<class 'vobject.icalendar.VCalendar2'>"
    assert behavior.is_component
    assert get_behavior("invalid_name") is None

    # test for ContentLine (not a component)
    non_component_behavior = get_behavior("RDATE")
    assert not non_component_behavior.is_component


def test_multi_date_behavior():
    """Test MultiDateBehavior"""
    parse_rdate = MultiDateBehavior.transform_to_native
    assert str(parse_rdate(text_line_to_content_line("RDATE;VALUE=DATE:19970304,19970504,19970704,19970904"))) == (
        "<RDATE{'VALUE': ['DATE']}[datetime.date(1997, 3, 4), datetime.date(1997, 5, 4), "
        "datetime.date(1997, 7, 4), datetime.date(1997, 9, 4)]>"
    )
    assert str(
        parse_rdate(
            text_line_to_content_line("RDATE;VALUE=PERIOD:19960403T020000Z/19960403T040000Z,19960404T010000Z/PT3H")
        )
    ) == (
        "<RDATE{'VALUE': ['PERIOD']}[(datetime.datetime(1996, 4, 3, 2, 0, tzinfo=tzutc()), datetime.datetime"
        "(1996, 4, 3, 4, 0, tzinfo=tzutc())), (datetime.datetime(1996, 4, 4, 1, 0, tzinfo=tzutc()), "
        + "datetime.timedelta(seconds=10800))]>"
    )


def test_period_behavior():
    """Test PeriodBehavior"""
    line = ContentLine("test", [], "", is_native=True)
    line.behavior = PeriodBehavior
    line.value = [(dt.datetime(2006, 2, 16, 10), two_hours)]

    assert line.transform_from_native().value == "20060216T100000/PT2H"
    assert line.transform_to_native().value == [(dt.datetime(2006, 2, 16, 10, 0), dt.timedelta(0, 7200))]

    line.value.append((dt.datetime(2006, 5, 16, 10), two_hours))

    assert line.serialize().strip() == "TEST:20060216T100000/PT2H,20060516T100000/PT2H"
