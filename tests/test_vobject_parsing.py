"""General tests for parsing ics files."""

import datetime as dt

import pytest
from dateutil.tz import tzutc

from vobject import read_components, read_one
from vobject.base import ParseError, parse_params

from .common import get_test_file


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

    # assert str(c.vevent.dtstart.value) == "2002-10-28 14:00:00-08:00" # Fixme
    assert isinstance(c.vevent.dtstart.value, dt.datetime)
    assert str(c.vevent.dtend.value) == "2002-10-28 15:00:00-08:00"
    assert isinstance(c.vevent.dtend.value, dt.datetime)
    assert c.vevent.dtstamp.value == dt.datetime(2002, 10, 28, 1, 17, 6, tzinfo=tzutc())

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
