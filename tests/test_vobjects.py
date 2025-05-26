import datetime as dt

import pytest

from vobjectx import read_one
from vobjectx.base import get_behavior, new_from_behavior, parse_line, read_components
from vobjectx.exceptions import ParseError

from .common import get_test_file


# pylint:disable = W0621
@pytest.fixture(scope="module")
def class_setup():
    return {
        "vcard_file": get_test_file("vcard_with_groups.ics"),
        "simple_test_cal": get_test_file("simple_test.ics"),
        "vtodo_file": get_test_file("vtodo.ics"),
    }


def test_vcard_creation():
    vcard = new_from_behavior("vcard", "3.0")
    assert str(vcard) == "<VCARD| []>"


def test_default_behavior(class_setup):
    card = read_one(class_setup["vcard_file"])
    assert get_behavior("note") is None
    expected = "The Mayor of the great city of Goerlitz in the great country of Germany.\nNext line."
    assert str(card.note.value) == expected


def test_with_groups(class_setup):
    card = read_one(class_setup["vcard_file"])
    assert str(card.group) == "home"
    assert str(card.tel.group) == "home"

    card.group = card.tel.group = "new"
    assert str(card.tel.serialize().strip()) == "new.TEL;TYPE=fax,voice,msg:+49 3581 123456"
    assert str(card.serialize().splitlines()[0]) == "new.BEGIN:VCARD"


def test_vcard_3_parsing():
    card = read_one(get_test_file("simple_3_0_test.ics"))
    assert card.org.value == ["University of Novosibirsk", "Department of Octopus Parthenogenesis"]

    for _ in range(3):
        new_card = read_one(card.serialize())
        assert new_card.org.value == card.org.value
        card = new_card


def test_read_components(class_setup):
    cal = next(read_components(class_setup["simple_test_cal"]))

    assert str(cal) == "<VCALENDAR| [<VEVENT| [<SUMMARY{'BLAH': ['hi!']}Bastille Day Party>]>]>"
    assert str(cal.vevent.summary) == "<SUMMARY{'BLAH': ['hi!']}Bastille Day Party>"


def test_parse_line():
    assert parse_line("BLAH:") == ("BLAH", [], "", None)
    assert parse_line("RDATE:VALUE=DATE:19970304,19970504,19970704,19970904") == (
        "RDATE",
        [],
        "VALUE=DATE:19970304,19970504,19970704,19970904",
        None,
    )
    assert parse_line(
        'DESCRIPTION;ALTREP="http://www.wiz.org":The Fall 98 Wild Wizards Conference - - Las Vegas, NV, USA'
    ) == (
        "DESCRIPTION",
        [["ALTREP", "http://www.wiz.org"]],
        "The Fall 98 Wild Wizards Conference - - Las Vegas, NV, USA",
        None,
    )
    assert parse_line("EMAIL;PREF;INTERNET:john@nowhere.com") == (
        "EMAIL",
        [["PREF"], ["INTERNET"]],
        "john@nowhere.com",
        None,
    )
    assert parse_line('EMAIL;TYPE="blah",hah;INTERNET="DIGI",DERIDOO:john@nowhere.com') == (
        "EMAIL",
        [["TYPE", "blah", "hah"], ["INTERNET", "DIGI", "DERIDOO"]],
        "john@nowhere.com",
        None,
    )
    assert parse_line("item1.ADR;type=HOME;type=pref:;;Reeperbahn 116;Hamburg;;20359;") == (
        "ADR",
        [["type", "HOME"], ["type", "pref"]],
        ";;Reeperbahn 116;Hamburg;;20359;",
        "item1",
    )
    with pytest.raises(ParseError):
        parse_line(":")


def test_vtodo(class_setup):
    obj = read_one(class_setup["vtodo_file"])
    obj.vtodo.add("completed")
    obj.vtodo.completed.value = dt.datetime(2015, 5, 5, 13, 30)
    assert obj.vtodo.completed.serialize()[:23] == "COMPLETED:20150505T1330"
    obj = read_one(obj.serialize())
    assert obj.vtodo.completed.value == dt.datetime(2015, 5, 5, 13, 30)
