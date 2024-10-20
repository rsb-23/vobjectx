# -*- coding: utf-8 -*-
import datetime as dt
import json
import unittest

import dateutil
from dateutil.tz import tzutc

from vobject import iCalendar
from vobject.base import ContentLine, ParseError
from vobject.base import __behavior_registry as behavior_registry
from vobject.base import (
    get_behavior,
    new_from_behavior,
    parse_line,
    parse_params,
    read_components,
    read_one,
    text_line_to_content_line,
)
from vobject.change_tz import change_tz
from vobject.icalendar import MultiDateBehavior, PeriodBehavior

from .common import TEST_FILE_DIR, get_test_file, two_hours


class TestCalendarSerializing(unittest.TestCase):
    """
    Test creating an iCalendar file
    """

    max_diff = None

    def test_scratchbuild(self):
        """
        CreateCalendar 2.0 format from scratch
        """
        test_cal = get_test_file("simple_2_0_test.ics")
        cal = new_from_behavior("vcalendar", "2.0")
        cal.add("vevent")
        cal.vevent.add("dtstart").value = dt.datetime(2006, 5, 9)
        cal.vevent.add("description").value = "Test event"
        cal.vevent.add("created").value = dt.datetime(
            2006, 1, 1, 10, tzinfo=dateutil.tz.tzical(f"{TEST_FILE_DIR}/timezones.ics").get("US/Pacific")
        )
        cal.vevent.add("uid").value = "Not very random UID"
        cal.vevent.add("dtstamp").value = dt.datetime(2017, 6, 26, 0, tzinfo=tzutc())

        cal.vevent.add("attendee").value = "mailto:froelich@example.com"
        cal.vevent.attendee.params["CN"] = ["Fröhlich"]

        # Note we're normalizing line endings, because no one got time for that.
        self.assertEqual(cal.serialize().replace("\r\n", "\n"), test_cal.replace("\r\n", "\n"))

    def test_unicode(self):
        """
        Test unicode characters
        """

        def common_checks(test_cal_):
            vevent = read_one(test_cal_).vevent
            vevent2 = read_one(vevent.serialize())
            self.assertEqual(str(vevent), str(vevent2))
            self.assertEqual(vevent.summary.value, "The title こんにちはキティ")

        test_cal = get_test_file("utf8_test.ics")
        common_checks(test_cal)

    def test_wrapping(self):
        """
        Should support input file with a long text field covering multiple lines
        """
        test_journal = get_test_file("journal.ics")
        vobj = read_one(test_journal)
        vjournal = read_one(vobj.serialize())
        self.assertTrue("Joe, Lisa, and Bob" in vjournal.description.value)
        self.assertTrue("Tuesday.\n2." in vjournal.description.value)

    def test_multiline(self):
        """
        Multi-text serialization test
        """
        category = new_from_behavior("categories")
        category.value = ["Random category"]
        self.assertEqual(category.serialize().strip(), "CATEGORIES:Random category")

        category.value.append("Other category")
        self.assertEqual(category.serialize().strip(), "CATEGORIES:Random category,Other category")

    def test_semicolon_separated(self):
        """
        Semi-colon separated multi-text serialization test
        """
        request_status = new_from_behavior("request-status")
        request_status.value = ["5.1", "Service unavailable"]
        self.assertEqual(request_status.serialize().strip(), "REQUEST-STATUS:5.1;Service unavailable")

    @staticmethod
    def test_unicode_multiline():
        """
        Test multiline unicode characters
        """
        cal = iCalendar()
        cal.add("method").value = "REQUEST"
        cal.add("vevent")
        cal.vevent.add("created").value = dt.datetime.now()
        cal.vevent.add("summary").value = "Классное событие"
        cal.vevent.add("description").value = (
            "Классное событие Классное событие Классное событие Классное событие "
            "Классное событие Классsdssdное событие"
        )

        # json tries to encode as utf-8 and it would break if some chars could not be encoded
        json.dumps(cal.serialize())

    @staticmethod
    def test_ical_to_hcal():
        """
        Serializing iCalendar to hCalendar.

        Since Hcalendar is experimental and the behavior doesn't seem to want to load,
        This test will have to wait.


        tzs = dateutil.tz.tzical("test_files/timezones.ics")
        cal = new_from_behavior('hcalendar')
        self.assertEqual(
            str(cal.behavior),
            "<class 'vobject.hcalendar.HCalendar'>"
        )
        cal.add('vevent')
        cal.vevent.add('summary').value = "this is a note"
        cal.vevent.add('url').value = "http://microformats.org/code/hcalendar/creator"
        cal.vevent.add('dtstart').value = datetime.date(2006,2,27)
        cal.vevent.add('location').value = "a place"
        cal.vevent.add('dtend').value = datetime.date(2006,2,27) + datetime.timedelta(days = 2)

        event2 = cal.add('vevent')
        event2.add('summary').value = "Another one"
        event2.add('description').value = "The greatest thing ever!"
        event2.add('dtstart').value = datetime.datetime(1998, 12, 17, 16, 42, tzinfo = tzs.get('US/Pacific'))
        event2.add('location').value = "somewhere else"
        event2.add('dtend').value = event2.dtstart.value + datetime.timedelta(days = 6)
        hcal = cal.serialize()
        """
        # self.assertEqual(
        #    str(hcal),
        #    """<span class="vevent">
        #           <a class="url" href="http://microformats.org/code/hcalendar/creator">
        #             <span class="summary">this is a note</span>:
        #              <abbr class="dtstart", title="20060227">Monday, February 27</abbr>
        #              - <abbr class="dtend", title="20060301">Tuesday, February 28</abbr>
        #              at <span class="location">a place</span>
        #           </a>
        #        </span>
        #        <span class="vevent">
        #           <span class="summary">Another one</span>:
        #           <abbr class="dtstart", title="19981217T164200-0800">Thursday, December 17, 16:42</abbr>
        #           - <abbr class="dtend", title="19981223T164200-0800">Wednesday, December 23, 16:42</abbr>
        #           at <span class="location">somewhere else</span>
        #           <div class="description">The greatest thing ever!</div>
        #        </span>
        #    """
        # )


class TestBehaviors(unittest.TestCase):
    """
    Test Behaviors
    """

    def test_general_behavior(self):
        """
        Tests for behavior registry, getting and creating a behavior.
        """
        # Check expected behavior registry.
        self.assertEqual(
            sorted(behavior_registry.keys()),
            [
                "",
                "ACTION",
                "ADR",
                "AVAILABLE",
                "BUSYTYPE",
                "CALSCALE",
                "CATEGORIES",
                "CLASS",
                "COMMENT",
                "COMPLETED",
                "CONTACT",
                "CREATED",
                "DAYLIGHT",
                "DESCRIPTION",
                "DTEND",
                "DTSTAMP",
                "DTSTART",
                "DUE",
                "DURATION",
                "EXDATE",
                "EXRULE",
                "FN",
                "FREEBUSY",
                "GEO",
                "LABEL",
                "LAST-MODIFIED",
                "LOCATION",
                "METHOD",
                "N",
                "ORG",
                "PHOTO",
                "PRODID",
                "RDATE",
                "RECURRENCE-ID",
                "RELATED-TO",
                "REQUEST-STATUS",
                "RESOURCES",
                "RRULE",
                "STANDARD",
                "STATUS",
                "SUMMARY",
                "TRANSP",
                "TRIGGER",
                "UID",
                "VALARM",
                "VAVAILABILITY",
                "VCALENDAR",
                "VCARD",
                "VEVENT",
                "VFREEBUSY",
                "VJOURNAL",
                "VTIMEZONE",
                "VTODO",
            ],
        )

        # test get_behavior
        behavior = get_behavior("VCALENDAR")
        self.assertEqual(str(behavior), "<class 'vobject.icalendar.VCalendar2'>")
        self.assertTrue(behavior.is_component)

        self.assertEqual(get_behavior("invalid_name"), None)
        # test for ContentLine (not a component)
        non_component_behavior = get_behavior("RDATE")
        self.assertFalse(non_component_behavior.is_component)

    def test_MultiDateBehavior(self):
        """
        Test MultiDateBehavior
        """
        parse_rdate = MultiDateBehavior.transform_to_native
        self.assertEqual(
            str(parse_rdate(text_line_to_content_line("RDATE;VALUE=DATE:19970304,19970504,19970704,19970904"))),
            "<RDATE{'VALUE': ['DATE']}[datetime.date(1997, 3, 4), datetime.date(1997, 5, 4), "
            "datetime.date(1997, 7, 4), datetime.date(1997, 9, 4)]>",
        )
        self.assertEqual(
            str(
                parse_rdate(
                    text_line_to_content_line(
                        "RDATE;VALUE=PERIOD:19960403T020000Z/19960403T040000Z,19960404T010000Z/PT3H"
                    )
                )
            ),
            "<RDATE{'VALUE': ['PERIOD']}[(datetime.datetime(1996, 4, 3, 2, 0, tzinfo=tzutc()), datetime.datetime"
            "(1996, 4, 3, 4, 0, tzinfo=tzutc())), (datetime.datetime(1996, 4, 4, 1, 0, tzinfo=tzutc()), "
            + "datetime.timedelta(seconds=10800))]>",
        )

    def test_period_behavior(self):
        """
        Test PeriodBehavior
        """
        line = ContentLine("test", [], "", is_native=True)
        line.behavior = PeriodBehavior
        line.value = [(dt.datetime(2006, 2, 16, 10), two_hours)]

        self.assertEqual(line.transform_from_native().value, "20060216T100000/PT2H")
        self.assertEqual(line.transform_to_native().value, [(dt.datetime(2006, 2, 16, 10, 0), dt.timedelta(0, 7200))])

        line.value.append((dt.datetime(2006, 5, 16, 10), two_hours))

        self.assertEqual(line.serialize().strip(), "TEST:20060216T100000/PT2H,20060516T100000/PT2H")


class TestVTodo(unittest.TestCase):
    """
    VTodo Tests
    """

    def test_vtodo(self):
        """
        Test VTodo
        """
        vtodo = get_test_file("vtodo.ics")
        obj = read_one(vtodo)
        obj.vtodo.add("completed")
        obj.vtodo.completed.value = dt.datetime(2015, 5, 5, 13, 30)
        self.assertEqual(obj.vtodo.completed.serialize()[:23], "COMPLETED:20150505T1330")
        obj = read_one(obj.serialize())
        self.assertEqual(obj.vtodo.completed.value, dt.datetime(2015, 5, 5, 13, 30))


class TestVobject(unittest.TestCase):
    """
    VObject Tests
    """

    max_diff = None

    @classmethod
    def setUpClass(cls):
        """
        Method for setting up class fixture before running tests in the class.
        Fetches test file.
        """
        cls.simple_test_cal = get_test_file("simple_test.ics")

    def test_read_components(self):
        """
        Test if reading components correctly
        """
        cal = next(read_components(self.simple_test_cal))

        self.assertEqual(str(cal), "<VCALENDAR| [<VEVENT| [<SUMMARY{'BLAH': ['hi!']}Bastille Day Party>]>]>")
        self.assertEqual(str(cal.vevent.summary), "<SUMMARY{'BLAH': ['hi!']}Bastille Day Party>")

    def test_parse_line(self):
        """
        Test line parsing
        """
        self.assertEqual(parse_line("BLAH:"), ("BLAH", [], "", None))
        self.assertEqual(
            parse_line("RDATE:VALUE=DATE:19970304,19970504,19970704,19970904"),
            ("RDATE", [], "VALUE=DATE:19970304,19970504,19970704,19970904", None),
        )
        self.assertEqual(
            parse_line(
                'DESCRIPTION;ALTREP="http://www.wiz.org":The Fall 98 Wild Wizards Conference - - Las Vegas, NV, USA'
            ),
            (
                "DESCRIPTION",
                [["ALTREP", "http://www.wiz.org"]],
                "The Fall 98 Wild Wizards Conference - - Las Vegas, NV, USA",
                None,
            ),
        )
        self.assertEqual(
            parse_line("EMAIL;PREF;INTERNET:john@nowhere.com"),
            ("EMAIL", [["PREF"], ["INTERNET"]], "john@nowhere.com", None),
        )
        self.assertEqual(
            parse_line('EMAIL;TYPE="blah",hah;INTERNET="DIGI",DERIDOO:john@nowhere.com'),
            ("EMAIL", [["TYPE", "blah", "hah"], ["INTERNET", "DIGI", "DERIDOO"]], "john@nowhere.com", None),
        )
        self.assertEqual(
            parse_line("item1.ADR;type=HOME;type=pref:;;Reeperbahn 116;Hamburg;;20359;"),
            ("ADR", [["type", "HOME"], ["type", "pref"]], ";;Reeperbahn 116;Hamburg;;20359;", "item1"),
        )
        self.assertRaises(ParseError, parse_line, ":")


class TestGeneralFileParsing(unittest.TestCase):
    """
    General tests for parsing ics files.
    """

    def test_read_one(self):
        """
        Test reading first component of ics
        """
        cal = get_test_file("silly_test.ics")
        silly = read_one(cal)
        self.assertEqual(
            str(silly),
            "<SILLYPROFILE| [<MORESTUFF{}this line is not folded, but in practice probably ought to be, as it is"
            " exceptionally long, and moreover demonstratively stupid>, <SILLYNAME{}name>, <STUFF{}foldedline>]>",
        )
        self.assertEqual(str(silly.stuff), "<STUFF{}foldedline>")

    def test_importing(self):
        """
        Test importing ics
        """
        cal = get_test_file("standard_test.ics")
        c = read_one(cal, validate=True)
        self.assertEqual(str(c.vevent.valarm.trigger), "<TRIGGER{}-1 day, 0:00:00>")

        self.assertEqual(str(c.vevent.dtstart.value), "2002-10-28 14:00:00-08:00")
        self.assertTrue(isinstance(c.vevent.dtstart.value, dt.datetime))
        self.assertEqual(str(c.vevent.dtend.value), "2002-10-28 15:00:00-08:00")
        self.assertTrue(isinstance(c.vevent.dtend.value, dt.datetime))
        self.assertEqual(c.vevent.dtstamp.value, dt.datetime(2002, 10, 28, 1, 17, 6, tzinfo=tzutc()))

        vevent = c.vevent.transform_from_native()
        self.assertEqual(str(vevent.rrule), "<RRULE{}FREQ=Weekly;COUNT=10>")

    def test_bad_stream(self):
        """
        Test bad ics stream
        """
        cal = get_test_file("badstream.ics")
        self.assertRaises(ParseError, read_one, cal)

    def test_bad_line(self):
        """
        Test bad line in ics file
        """
        cal = get_test_file("badline.ics")
        self.assertRaises(ParseError, read_one, cal)

        newcal = read_one(cal, ignore_unreadable=True)
        self.assertEqual(str(newcal.vevent.x_bad_underscore), "<X-BAD-UNDERSCORE{}TRUE>")

    def test_parse_params(self):
        """
        Test parsing parameters
        """
        self.assertEqual(parse_params(';ALTREP="http://www.wiz.org"'), [["ALTREP", "http://www.wiz.org"]])
        self.assertEqual(
            parse_params(';ALTREP="http://www.wiz.org;;",Blah,Foo;NEXT=Nope;BAR'),
            [["ALTREP", "http://www.wiz.org;;", "Blah", "Foo"], ["NEXT", "Nope"], ["BAR"]],
        )

    def test_quoted_printable(self):
        """
        The use of QUOTED-PRINTABLE encoding
        """
        ics_str = get_test_file("quoted-printable.ics")
        vobjs = read_components(ics_str, allow_qp=True)
        for vo in vobjs:
            self.assertIsNotNone(vo)


class TestVcards(unittest.TestCase):
    """
    Test VCards
    """

    test_file = None

    @classmethod
    def setUpClass(cls):
        """
        Method for setting up class fixture before running tests in the class.
        Fetches test file.
        """
        cls.test_file = get_test_file("vcard_with_groups.ics")
        cls.card = read_one(cls.test_file)

    def test_vcard_creation(self):
        """
        Test creating a vCard
        """
        vcard = new_from_behavior("vcard", "3.0")
        self.assertEqual(str(vcard), "<VCARD| []>")

    def test_default_behavior(self):
        """
        Default behavior test.
        """
        card = self.card
        self.assertEqual(get_behavior("note"), None)
        self.assertEqual(
            str(card.note.value), "The Mayor of the great city of Goerlitz in the great country of Germany.\nNext line."
        )

    def test_with_groups(self):
        """
        vCard groups test
        """
        card = self.card
        self.assertEqual(str(card.group), "home")
        self.assertEqual(str(card.tel.group), "home")

        card.group = card.tel.group = "new"
        self.assertEqual(str(card.tel.serialize().strip()), "new.TEL;TYPE=fax,voice,msg:+49 3581 123456")
        self.assertEqual(str(card.serialize().splitlines()[0]), "new.BEGIN:VCARD")

    def test_vcard_3_parsing(self):
        """
        VCARD 3.0 parse test
        """
        test_file = get_test_file("simple_3_0_test.ics")
        card = read_one(test_file)
        # value not rendering correctly?
        # self.assertEqual(
        #    card.adr.value,
        #    "<Address: Haight Street 512;\nEscape, Test\nNovosibirsk,  80214\nGnuland>"
        # )
        self.assertEqual(card.org.value, ["University of Novosibirsk", "Department of Octopus Parthenogenesis"])

        for _ in range(3):
            new_card = read_one(card.serialize())
            self.assertEqual(new_card.org.value, card.org.value)
            card = new_card


class TestChangeTZ(unittest.TestCase):
    """
    Tests for change_tz.change_tz
    """

    class StubCal:
        class StubEvent:
            class Node:
                def __init__(self, value):
                    self.value = value

            def __init__(self, dtstart, dtend):
                self.dtstart = self.Node(dtstart)
                self.dtend = self.Node(dtend)

        def __init__(self, dates):
            """
            dates is a list of tuples (dtstart, dtend)
            """
            self.vevent_list = [self.StubEvent(*d) for d in dates]

    def test_change_tz(self):
        """
        Change the timezones of events in a component to a different
        timezone
        """

        # Setup - create a stub vevent list
        old_tz = dateutil.tz.gettz("UTC")  # 0:00
        new_tz = dateutil.tz.gettz("America/Chicago")  # -5:00

        dates = [
            (
                dt.datetime(1999, 12, 31, 23, 59, 59, 0, tzinfo=old_tz),
                dt.datetime(2000, 1, 1, 0, 0, 0, 0, tzinfo=old_tz),
            ),
            (
                dt.datetime(2010, 12, 31, 23, 59, 59, 0, tzinfo=old_tz),
                dt.datetime(2011, 1, 2, 3, 0, 0, 0, tzinfo=old_tz),
            ),
        ]

        cal = self.StubCal(dates)

        # Exercise - change the timezone
        change_tz(cal, new_tz, dateutil.tz.gettz("UTC"))

        # Test - that the tzs were converted correctly
        expected_new_dates = [
            (
                dt.datetime(1999, 12, 31, 17, 59, 59, 0, tzinfo=new_tz),
                dt.datetime(1999, 12, 31, 18, 0, 0, 0, tzinfo=new_tz),
            ),
            (
                dt.datetime(2010, 12, 31, 17, 59, 59, 0, tzinfo=new_tz),
                dt.datetime(2011, 1, 1, 21, 0, 0, 0, tzinfo=new_tz),
            ),
        ]

        for vevent, expected_datepair in zip(cal.vevent_list, expected_new_dates):
            self.assertEqual(vevent.dtstart.value, expected_datepair[0])
            self.assertEqual(vevent.dtend.value, expected_datepair[1])

    def test_change_tz_utc_only(self):
        """
        Change any UTC timezones of events in a component to a different
        timezone
        """

        # Setup - create a stub vevent list
        utc_tz = dateutil.tz.gettz("UTC")  # 0:00
        non_utc_tz = dateutil.tz.gettz("America/Santiago")  # -4:00
        new_tz = dateutil.tz.gettz("America/Chicago")  # -5:00

        dates = [
            (
                dt.datetime(1999, 12, 31, 23, 59, 59, 0, tzinfo=utc_tz),
                dt.datetime(2000, 1, 1, 0, 0, 0, 0, tzinfo=non_utc_tz),
            )
        ]

        cal = self.StubCal(dates)

        # Exercise - change the timezone passing utc_only=True
        change_tz(cal, new_tz, dateutil.tz.gettz("UTC"), utc_only=True)

        # Test - that only the utc item has changed
        expected_new_dates = [(dt.datetime(1999, 12, 31, 17, 59, 59, 0, tzinfo=new_tz), dates[0][1])]

        for vevent, expected_datepair in zip(cal.vevent_list, expected_new_dates):
            self.assertEqual(vevent.dtstart.value, expected_datepair[0])
            self.assertEqual(vevent.dtend.value, expected_datepair[1])

    def test_change_tz_default(self):
        """
        Change the timezones of events in a component to a different
        timezone, passing a default timezone that is assumed when the events
        don't have one
        """

        # Setup - create a stub vevent list
        new_tz = dateutil.tz.gettz("America/Chicago")  # -5:00

        dates = [
            (dt.datetime(1999, 12, 31, 23, 59, 59, 0, tzinfo=None), dt.datetime(2000, 1, 1, 0, 0, 0, 0, tzinfo=None))
        ]

        cal = self.StubCal(dates)

        # Exercise - change the timezone
        change_tz(cal, new_tz, dateutil.tz.gettz("UTC"))

        # Test - that the tzs were converted correctly
        expected_new_dates = [
            (
                dt.datetime(1999, 12, 31, 17, 59, 59, 0, tzinfo=new_tz),
                dt.datetime(1999, 12, 31, 18, 0, 0, 0, tzinfo=new_tz),
            )
        ]

        for vevent, expected_datepair in zip(cal.vevent_list, expected_new_dates):
            self.assertEqual(vevent.dtstart.value, expected_datepair[0])
            self.assertEqual(vevent.dtend.value, expected_datepair[1])


if __name__ == "__main__":
    unittest.main(buffer=True, failfast=True)
