import datetime as dt
import json

import dateutil
from dateutil.tz import tzutc

from vobjectx import VERSION, iCalendar, new_from_behavior, read_one

from .common import TEST_FILE_DIR, get_test_file


def test_scratchbuild():
    """CreateCalendar 2.0 format from scratch"""
    test_cal = get_test_file("simple_2_0_test.ics") % VERSION
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
    assert cal.serialize().replace("\r\n", "\n") == test_cal.replace("\r\n", "\n")


def test_unicode():
    """Test unicode characters"""

    def common_checks(test_cal_):
        vevent = read_one(test_cal_).vevent
        vevent2 = read_one(vevent.serialize())
        assert str(vevent) == str(vevent2)
        assert vevent.summary.value == "The title こんにちはキティ"

    test_cal = get_test_file("utf8_test.ics")
    common_checks(test_cal)


def test_wrapping():
    """Should support input file with a long text field covering multiple lines"""
    test_journal = get_test_file("journal.ics")
    vobj = read_one(test_journal)
    vjournal = read_one(vobj.serialize())
    assert "Joe, Lisa, and Bob" in vjournal.description.value
    assert "Tuesday.\n2." in vjournal.description.value


def test_multiline():
    """Multi-text serialization test"""
    category = new_from_behavior("categories")
    category.value = ["Random category"]
    assert category.serialize().strip() == "CATEGORIES:Random category"

    category.value.append("Other category")
    assert category.serialize().strip() == "CATEGORIES:Random category,Other category"


def test_semicolon_separated():
    """Semi-colon separated multi-text serialization test"""
    request_status = new_from_behavior("request-status")
    request_status.value = ["5.1", "Service unavailable"]
    assert request_status.serialize().strip() == "REQUEST-STATUS:5.1;Service unavailable"


def test_unicode_multiline():
    """Test multiline unicode characters"""
    cal = iCalendar()
    cal.add("method").value = "REQUEST"
    cal.add("vevent")
    cal.vevent.add("created").value = dt.datetime.now()
    cal.vevent.add("summary").value = "Классное событие"
    cal.vevent.add("description").value = (
        "Классное событие Классное событие Классное событие Классное событие Классное событие Классsdssdное событие"
    )

    # json tries to encode as utf-8 and it would break if some chars could not be encoded
    json.dumps(cal.serialize())


def test_ical_to_hcal():
    """
    Serializing iCalendar to hCalendar.

    Since Hcalendar is experimental and the behavior doesn't seem to want to load,
    This test will have to wait.


    tzs = dateutil.tz.tzical("test_files/timezones.ics")
    cal = new_from_behavior('hcalendar')
    self.assertEqual(
        str(cal.behavior),
        "<class 'vobjectx.hcalendar.HCalendar'>"
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
