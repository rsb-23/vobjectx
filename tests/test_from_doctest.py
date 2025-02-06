import datetime as dt
from io import StringIO

from dateutil import rrule

import vobject as vo
from vobject.vcard import Name

from .common import get_test_file


def test_get_logical_lines():
    """Converted from doctest of vobject/base.py"""
    test_lines = (
        "Line 0 text\n , Line 0 continued.\n"
        "Line 1;encoding=quoted-printable:this is an evil=\n evil=\n format.\n"
        "Line 2 is a new line, it does not start with whitespace."
    )
    expected = [
        "Line 0 text, Line 0 continued.",
        "Line 1;encoding=quoted-printable:this is an evil=\n evil=\n format.",
        "Line 2 is a new line, it does not start with whitespace.",
    ]
    result = [line for line, _ in vo.base.get_logical_lines(StringIO(test_lines))]
    assert result == expected


def test_vobject():
    """Converted from doctest of vobject/__init__.py"""
    x = vo.iCalendar()
    x.add("vevent")
    assert str(x) == "<VCALENDAR| [<VEVENT| []>]>"

    v, utc = x.vevent, vo.icalendar.utc
    v.add("dtstart").value = dt.datetime(2004, 12, 15, 14, tzinfo=utc)
    assert str(v) == "<VEVENT| [<DTSTART{}2004-12-15 14:00:00+00:00>]>"
    assert str(x) == "<VCALENDAR| [<VEVENT| [<DTSTART{}2004-12-15 14:00:00+00:00>]>]>"

    newrule = rrule.rruleset()
    newrule.rrule(rrule.rrule(rrule.WEEKLY, count=2, dtstart=v.dtstart.value))
    v.rruleset = newrule
    assert list(v.rruleset) == [
        dt.datetime(2004, 12, 15, 14, 0, tzinfo=utc),
        dt.datetime(2004, 12, 22, 14, 0, tzinfo=utc),
    ]

    v.add("uid").value = "randomuid@MYHOSTNAME"
    v.add("dtstamp").value = dt.datetime(2006, 2, 15, 0, tzinfo=utc)

    assert x.serialize() == (
        f"BEGIN:VCALENDAR\r\nVERSION:2.0\r\nPRODID:-//VOBJECTX//NONSGML Version {vo.VERSION}//EN\r\n"
        "BEGIN:VEVENT\r\nUID:randomuid@MYHOSTNAME\r\nDTSTART:20041215T140000Z\r\n"
        "DTSTAMP:20060215T000000Z\r\n"  # not in actual test, newly added
        "RRULE:FREQ=WEEKLY;COUNT=2\r\nEND:VEVENT\r\nEND:VCALENDAR\r\n"
    )


def test_unicode_in_vcards():
    card = vo.vCard()
    card.add("fn").value = "Hello\u1234 World!"
    card.add("n").value = vo.vcard.Name("World", "Hello\u1234")
    card.add("adr").value = vo.vcard.Address("5\u1234 Nowhere, Apt 1", "Berkeley", "CA", "94704", "USA")
    assert (
        str(card)
        == "<VCARD| [<ADR{}5ሴ Nowhere, Apt 1\nBerkeley, CA 94704\nUSA>, <FN{}Helloሴ World!>, <N{} Helloሴ  World >]>"
    )
    assert card.serialize() == (
        "BEGIN:VCARD\r\nVERSION:3.0\r\nADR:;;5\u1234 Nowhere\\, Apt 1;Berkeley;CA;94704;USA\r\n"
        "FN:Hello\u1234 World!\r\nN:World;Hello\u1234;;;\r\nEND:VCARD\r\n"
    )

    # Equality in vCards
    assert card.adr.value != vo.vcard.Address("Just a street")
    assert card.adr.value == vo.vcard.Address("5\u1234 Nowhere, Apt 1", "Berkeley", "CA", "94704", "USA")

    # Organization (org)
    card.add("org").value = ["Company, Inc.", "main unit", "sub-unit"]
    assert card.org.serialize() == "ORG:Company\\, Inc.;main unit;sub-unit\r\n"


def _get_one_cal(filename):
    f = get_test_file(filename)
    return vo.read_one(f)


def test_ruby_rrule():
    """Ruby escapes semi-colons in rrules"""
    cal = _get_one_cal("ruby_rrule.ics")
    assert next(iter(cal.vevent.rruleset)) == dt.datetime(2003, 1, 1, 7, 0)


def test_tzid_commas():
    cal = _get_one_cal("ms_tzid.ics")
    assert str(cal.vevent.dtstart.value) == "2008-05-30 15:00:00+10:00"


def test_tzid_unicode():
    cal = _get_one_cal("tzid_8bit.ics")
    assert str(cal.vevent.dtstart.value) == "2008-05-30 15:00:00+06:00"
    assert cal.vevent.dtstart.serialize() == "DTSTART;TZID=Екатеринбург:20080530T150000\r\n"


def test_opensync_vcs():
    vcs = (
        "BEGIN:VCALENDAR\r\nPRODID:-//OpenSync//NONSGML OpenSync vformat 0.3//EN\r\nVERSION:1.0\r\n"
        "BEGIN:VEVENT\r\nDESCRIPTION;CHARSET=UTF-8;ENCODING=QUOTED-PRINTABLE:foo =C3=A5=0Abar =C3=A4=\r\n=0Abaz "
        "=C3=B6\r\nUID:20080406T152030Z-7822\r\nEND:VEVENT\r\nEND:VCALENDAR\r\n"
    )
    vcs = vo.read_one(vcs, allow_qp=True)
    assert vcs.serialize().startswith(
        "BEGIN:VCALENDAR\r\nVERSION:1.0\r\nPRODID:-//OpenSync//NONSGML OpenSync vformat 0.3//EN\r\n"
        "BEGIN:VEVENT\r\nUID:20080406T152030Z-7822\r\nDESCRIPTION;CHARSET=UTF-8:foo å\\nbar ä\\nbaz ö\r\n"
    )


def test_vcf_qp():
    vcf = (
        "BEGIN:VCARD\nVERSION:2.1\nN;ENCODING=QUOTED-PRINTABLE:;=E9\nFN;ENCODING=QUOTED-PRINTABLE:=E9\nTEL;"
        "HOME:0111111111\nEND:VCARD\n\n"
    )
    vcf = vo.read_one(vcf)
    assert vcf.n.value == Name(given="é")
    assert vcf.serialize() == "BEGIN:VCARD\r\nVERSION:2.1\r\nFN:é\r\nN:;é;;;\r\nTEL:0111111111\r\nEND:VCARD\r\n"
