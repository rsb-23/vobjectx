import datetime as dt
import unittest
from dataclasses import dataclass

from dateutil.tz import gettz

from vobject.change_tz import change_tz


@dataclass
class Node:
    value: str


class StubEvent:  # pylint:disable=R0903
    def __init__(self, dtstart, dtend):
        self.dtstart = Node(dtstart)
        self.dtend = Node(dtend)


class StubCal:  # pylint:disable=R0903
    def __init__(self, dates):
        """dates is a list of tuples (dtstart, dtend)"""
        self.vevent_list = [StubEvent(*d) for d in dates]


class TestChangeTZ(unittest.TestCase):
    """Tests for change_tz.change_tz"""

    def test_change_tz(self):
        """Change the timezones of events in a component to a different timezone"""
        # Setup - create a stub vevent list
        old_tz = gettz("UTC")  # 0:00
        new_tz = gettz("America/Chicago")  # -5:00

        dates = [
            (dt.datetime(1999, 12, 31, 23, 59, 59, tzinfo=old_tz), dt.datetime(2000, 1, 1, tzinfo=old_tz)),
            (dt.datetime(2010, 12, 31, 23, 59, 59, tzinfo=old_tz), dt.datetime(2011, 1, 2, 3, tzinfo=old_tz)),
        ]

        cal = StubCal(dates)

        # Exercise - change the timezone
        change_tz(cal, new_tz, gettz("UTC"))

        # Test - that the tzs were converted correctly
        expected_new_dates = [
            (dt.datetime(1999, 12, 31, 17, 59, 59, tzinfo=new_tz), dt.datetime(1999, 12, 31, 18, tzinfo=new_tz)),
            (dt.datetime(2010, 12, 31, 17, 59, 59, tzinfo=new_tz), dt.datetime(2011, 1, 1, 21, tzinfo=new_tz)),
        ]

        for vevent, expected_datepair in zip(cal.vevent_list, expected_new_dates):
            self.assertEqual(vevent.dtstart.value, expected_datepair[0])
            self.assertEqual(vevent.dtend.value, expected_datepair[1])

    def test_change_tz_utc_only(self):
        """Change any UTC timezones of events in a component to a different timezone"""

        # Setup - create a stub vevent list
        utc_tz = gettz("UTC")  # 0:00
        non_utc_tz = gettz("America/Santiago")  # -4:00
        new_tz = gettz("America/Chicago")  # -5:00

        dates = [(dt.datetime(1999, 12, 31, 23, 59, 59, tzinfo=utc_tz), dt.datetime(2000, 1, 1, tzinfo=non_utc_tz))]

        cal = StubCal(dates)

        # Exercise - change the timezone passing utc_only=True
        change_tz(cal, new_tz, gettz("UTC"), utc_only=True)

        # Test - that only the utc item has changed
        expected_new_dates = [(dt.datetime(1999, 12, 31, 17, 59, 59, tzinfo=new_tz), dates[0][1])]

        for vevent, expected_datepair in zip(cal.vevent_list, expected_new_dates):
            self.assertEqual(vevent.dtstart.value, expected_datepair[0])
            self.assertEqual(vevent.dtend.value, expected_datepair[1])

    def test_change_tz_default(self):
        """
        Change the timezones of events in a component to a different timezone, passing a default timezone that is
        assumed when the events don't have one
        """

        # Setup - create a stub vevent list
        new_tz = gettz("America/Chicago")  # -5:00

        dates = [(dt.datetime(1999, 12, 31, 23, 59, 59, tzinfo=None), dt.datetime(2000, 1, 1, tzinfo=None))]

        cal = StubCal(dates)

        # Exercise - change the timezone
        change_tz(cal, new_tz, gettz("UTC"))

        # Test - that the tzs were converted correctly
        expected_new_dates = [
            (dt.datetime(1999, 12, 31, 17, 59, 59, tzinfo=new_tz), dt.datetime(1999, 12, 31, 18, tzinfo=new_tz))
        ]

        for vevent, expected_datepair in zip(cal.vevent_list, expected_new_dates):
            self.assertEqual(vevent.dtstart.value, expected_datepair[0])
            self.assertEqual(vevent.dtend.value, expected_datepair[1])
