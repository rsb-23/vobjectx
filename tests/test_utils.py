import datetime as dt
from io import StringIO

from dateutil.tz import tzutc

from vobject.base import fold_one_line
from vobject.helper import indent_str
from vobject.icalendar import date_to_string, datetime_to_string
from vobject.vcard import to_list


def test_to_list():
    assert to_list("") == [""]
    assert to_list("Knudson") == ["Knudson"]


def test_indent_str():
    assert indent_str(level=2) == " " * 6
    assert indent_str(level=1, tabwidth=4) == " " * 4


def test_date_to_string():
    tc = {dt.date(2007, 5, 1): "20070501", dt.date(1997, 3, 17): "19970317"}
    for _date, out in tc.items():
        assert date_to_string(_date) == out


def test_datetime_to_string():
    tc = {
        (dt.datetime(2000, 10, 29, 3, 0), False): "20001029T030000",
        (dt.datetime(2007, 3, 13, 12, 34, 32, tzinfo=tzutc()), True): "20070313T123432Z",
    }
    for inp, out in tc.items():
        assert datetime_to_string(*inp) == out


def test_fold_one_line():
    test_input = (
        "DESCRIPTION:Классное событие Классное событие Классное событие Классное событие Классное "
        "событие Классsdssdное событие"
    )
    expected = (
        "DESCRIPTION:Классное событие Классное событие\r\n  Классное событие Классное событие "
        "Клас\r\n сное событие Классsdssdное событие\r\n"
    )
    buf = StringIO()
    fold_one_line(buf, test_input)
    assert buf.getvalue() == expected
