import datetime as dt
from io import StringIO
from unittest import TestCase, skip

import dateutil.rrule as rrule

import vobject as vo

from .common import get_test_file


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

    @staticmethod
    def _get_one_cal(filename):
        f = get_test_file(filename)
        return vo.read_one(f)

    def test_ruby_rrule(self):
        """Ruby escapes semi-colons in rrules"""
        cal = self._get_one_cal("ruby_rrule.ics")
        self.assertEqual(next(iter(cal.vevent.rruleset)), dt.datetime(2003, 1, 1, 7, 0))

    def test_tzid_commas(self):
        cal = self._get_one_cal("ms_tzid.ics")
        self.assertEqual(str(cal.vevent.dtstart.value), "2008-05-30 15:00:00+10:00")

    def test_tzid_unicode(self):
        cal = self._get_one_cal("tzid_8bit.ics")
        self.assertEqual(str(cal.vevent.dtstart.value), "2008-05-30 15:00:00+06:00")
        self.assertEqual(cal.vevent.dtstart.serialize(), "DTSTART;TZID=Екатеринбург:20080530T150000\r\n")

    @skip("test fails, to be checked")
    def test_opensync_vcs(self):
        vcs = (
            "BEGIN:VCALENDAR\r\nPRODID:-//OpenSync//NONSGML OpenSync vformat 0.3//EN\r\nVERSION:1.0\r\n"
            "BEGIN:VEVENT\r\nDESCRIPTION;CHARSET=UTF-8;ENCODING=QUOTED-PRINTABLE:foo =C3=A5=0Abar =C3=A4=\r\n=0Abaz "
            "=C3=B6\r\nUID:20080406T152030Z-7822\r\nEND:VEVENT\r\nEND:VCALENDAR\r\n"
        )
        vcs = vo.read_one(vcs, allow_qp=True)
        self.assertEqual(
            vcs.serialize(),
            "BEGIN:VCALENDAR\r\nVERSION:1.0\r\nPRODID:-//OpenSync//NONSGML OpenSync vformat 0.3//EN\r\n"
            "BEGIN:VEVENT\r\nUID:20080406T152030Z-7822\r\nDESCRIPTION:foo \xc3\xa5\\nbar \xc3\xa4\\nbaz \xc3\xb6\r\n"
            "END:VEVENT\r\nEND:VCALENDAR\r\n",
        )

    @skip("test fails, to be checked")
    def test_vcf_qp(self):
        vcf = (
            "BEGIN:VCARD\nVERSION:2.1\nN;ENCODING=QUOTED-PRINTABLE:;=E9\nFN;ENCODING=QUOTED-PRINTABLE:=E9\nTEL;"
            "HOME:0111111111\nEND:VCARD\n\n"
        )
        vcf = vo.read_one(vcf)
        self.assertEqual(vcf.n.value, "< Name:  ? >")
        self.assertEqual(vcf.n.value.given, "\xe9")
        self.assertEqual(
            vcf.serialize(),
            "BEGIN:VCARD\r\nVERSION:2.1\r\nFN:\xc3\xa9\r\nN:;\xc3\xa9;;;\r\nTEL:0111111111\r\nEND:VCARD\r\n",
        )
