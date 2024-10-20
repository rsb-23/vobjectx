import datetime as dt
from io import StringIO
from unittest import TestCase

import dateutil.rrule as rrule

import vobject as vo

from .common import TEST_FILE_DIR


class Doctest(TestCase):
    def test_get_logical_lines(self):
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
        self.assertEqual(result, expected)

    def test_vobject(self):
        """Converted from doctest of vobject/__init__.py"""
        x = vo.iCalendar()
        x.add("vevent")
        self.assertEqual(str(x), "<VCALENDAR| [<VEVENT| []>]>")

        v, utc = x.vevent, vo.icalendar.utc
        v.add("dtstart").value = dt.datetime(2004, 12, 15, 14, tzinfo=utc)
        self.assertEqual(str(v), "<VEVENT| [<DTSTART{}2004-12-15 14:00:00+00:00>]>")
        self.assertEqual(str(x), "<VCALENDAR| [<VEVENT| [<DTSTART{}2004-12-15 14:00:00+00:00>]>]>")

        newrule = rrule.rruleset()
        newrule.rrule(rrule.rrule(rrule.WEEKLY, count=2, dtstart=v.dtstart.value))
        v.rruleset = newrule
        self.assertEqual(
            list(v.rruleset),
            [dt.datetime(2004, 12, 15, 14, 0, tzinfo=utc), dt.datetime(2004, 12, 22, 14, 0, tzinfo=utc)],
        )

        v.add("uid").value = "randomuid@MYHOSTNAME"
        v.add("dtstamp").value = dt.datetime(2006, 2, 15, 0, tzinfo=utc)

        self.assertEqual(
            x.serialize(),
            "BEGIN:VCALENDAR\r\nVERSION:2.0\r\nPRODID:-//PYVOBJECT//NONSGML Version 1//EN\r\n"
            "BEGIN:VEVENT\r\nUID:randomuid@MYHOSTNAME\r\nDTSTART:20041215T140000Z\r\n"
            "DTSTAMP:20060215T000000Z\r\n"  # not in actual test, newly added
            "RRULE:FREQ=WEEKLY;COUNT=2\r\nEND:VEVENT\r\nEND:VCALENDAR\r\n",
        )


class MoreTests(TestCase):
    """Tests taken from more_tests.txt"""

    def test_unicode_in_vcards(self):
        card = vo.vCard()
        card.add("fn").value = "Hello\u1234 World!"
        card.add("n").value = vo.vcard.Name("World", "Hello\u1234")
        card.add("adr").value = vo.vcard.Address("5\u1234 Nowhere, Apt 1", "Berkeley", "CA", "94704", "USA")
        self.assertEqual(
            str(card),
            "<VCARD| [<ADR{}5ሴ Nowhere, Apt 1\nBerkeley, CA 94704\nUSA>, <FN{}Helloሴ World!>, <N{} Helloሴ  World >]>",
        )
        self.assertEqual(
            card.serialize(),
            "BEGIN:VCARD\r\nVERSION:3.0\r\nADR:;;5\u1234 Nowhere\\, Apt 1;Berkeley;CA;94704;USA\r\n"
            "FN:Hello\u1234 World!\r\nN:World;Hello\u1234;;;\r\nEND:VCARD\r\n",
        )

        # Equality in vCards
        self.assertNotEqual(card.adr.value, vo.vcard.Address("Just a street"))
        self.assertEqual(card.adr.value, vo.vcard.Address("5\u1234 Nowhere, Apt 1", "Berkeley", "CA", "94704", "USA"))

        # Organization (org)
        card.add("org").value = ["Company, Inc.", "main unit", "sub-unit"]
        self.assertEqual(card.org.serialize(), "ORG:Company\\, Inc.;main unit;sub-unit\r\n")

    def test_ruby_rrule(self):
        """Ruby escapes semi-colons in rrules"""
        with open(f"{TEST_FILE_DIR}/ruby_rrule.ics", "r") as f:
            cal = vo.read_one(f)
            self.assertEqual(next(iter(cal.vevent.rruleset)), dt.datetime(2003, 1, 1, 7, 0))
