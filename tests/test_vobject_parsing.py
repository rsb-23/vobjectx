"""General tests for parsing ics files."""

import datetime as dt
import io

import pytest

from vobjectx import read_components, read_one
from vobjectx.base import ParseError, get_logical_lines, parse_params

from .common import UTC_TZ, get_test_file


def test_read_one():
    """Test reading first component of ics"""
    cal = get_test_file("silly_test.ics")
    silly = read_one(cal)
    assert str(silly) == (
        "<SILLYPROFILE| [<MORESTUFF{}this line is not folded, but in practice probably ought to be, as it is"
        " exceptionally long, and moreover demonstratively stupid>, <SILLYNAME{}name>, <STUFF{}foldedline>]>"
    )
    assert str(silly.stuff) == "<STUFF{}foldedline>"


def test_importing():
    """Test importing ics"""
    cal = get_test_file("standard_test.ics")
    c = read_one(cal, validate=True)
    assert str(c.vevent.valarm.trigger) == "<TRIGGER{}-1 day, 0:00:00>"

    assert str(c.vevent.dtstart.value) == "2002-10-28 14:00:00-08:00"
    assert isinstance(c.vevent.dtstart.value, dt.datetime)
    assert str(c.vevent.dtend.value) == "2002-10-28 15:00:00-08:00"
    assert isinstance(c.vevent.dtend.value, dt.datetime)
    assert c.vevent.dtstamp.value == dt.datetime(2002, 10, 28, 1, 17, 6, tzinfo=UTC_TZ)

    vevent = c.vevent.transform_from_native()
    assert str(vevent.rrule) == "<RRULE{}FREQ=Weekly;COUNT=10>"


def test_bad_stream():
    """Test bad ics stream"""
    cal = get_test_file("badstream.ics")
    with pytest.raises(ParseError):
        read_one(cal)


def test_bad_line():
    """Test bad line in ics file"""
    cal = get_test_file("badline.ics")
    with pytest.raises(ParseError):
        read_one(cal)

    newcal = read_one(cal, ignore_unreadable=True)
    assert str(newcal.vevent.x_bad_underscore) == "<X-BAD-UNDERSCORE{}TRUE>"


def test_parse_params():
    """Test parsing parameters"""
    assert parse_params(';ALTREP="http://www.wiz.org"') == [["ALTREP", "http://www.wiz.org"]]
    assert parse_params(';ALTREP="http://www.wiz.org;;",Blah,Foo;NEXT=Nope;BAR') == [
        ["ALTREP", "http://www.wiz.org;;", "Blah", "Foo"],
        ["NEXT", "Nope"],
        ["BAR"],
    ]


def test_quoted_printable():
    """The use of QUOTED-PRINTABLE encoding"""
    ics_str = get_test_file("quoted-printable.ics")
    vobjs = read_components(ics_str, allow_qp=True)
    for vo in vobjs:
        assert vo is not None


def test_parsing_quopri_folded_value():
    """Test parsing of QUOTED-PRINTABLE folded logical lines."""
    raw = (
        "PROP1;PAR1;PAR2=PV:plain text\r\n"
        + "PROP2;PAR1;ENCODING=QUOTED-PRINTABLE:start =\r\n"
        + "middle=\r\n"
        + " end\r\n"
        + "PROP3;QUOTED-PRINTABLE:embedded newline >=0C=0A<\r\n"
        + "PROP4:plain text\r\n"
    )

    fp = io.StringIO(raw)
    lines = list(get_logical_lines(fp, allow_qp=True))
    assert len(lines) == 4
    assert lines[0][0] == "PROP1;PAR1;PAR2=PV:plain text"
    assert lines[0][1] == 1
    assert lines[1][0] == "PROP2;PAR1;ENCODING=QUOTED-PRINTABLE:start =\nmiddle=\n end"
    assert lines[1][1] == 2
    assert lines[2][0] == "PROP3;QUOTED-PRINTABLE:embedded newline >=0C=0A<"
    assert lines[2][1] == 5
    assert lines[3][0] == "PROP4:plain text"
    assert lines[3][1] == 6


def test_missing_object_terminator():
    """
    Test parsing of vObject without line terminator on final line.
    """
    empty_vcard = "BEGIN:VCARD{}END:VCARD"
    # Proper CRLF.
    card = read_one(empty_vcard.format("\r\n"))
    assert card is not None

    # LF-only (Unix-style).
    card = read_one(empty_vcard.format("\n"))
    assert card is not None

    # CR-only (old MacOS-style).
    card = read_one(empty_vcard.format("\r"))
    assert card is not None

    # Check with folded line too.
    card = read_one("BEGIN:VCARD\r\n" + "END:\r\n" + " VCARD")
    assert card is not None


def test_parsing_error_line_number():
    """
    Check that the line number reported for a parsing error is correct.
    """
    # Mismatched item names, with folded line.
    raw = "BEGIN:\r\n AAA\r\nEND:BBB"
    with pytest.raises(ParseError) as e:
        read_one(raw)

    # Check line number of parsing error.
    assert e.value.line_number == 3
