import datetime as dt

from vobjectx.icalendar import Component
from vobjectx.ics_diff import get_sort_key, sort_by_uid


def test_empty_list():
    assert sort_by_uid([]) == []


def test_single_component():
    component = Component("VEVENT")
    sorted_components = sort_by_uid([component])
    expected_sorted = [component]
    assert sorted_components == expected_sorted


def test_multiple_components():
    event1 = Component("VEVENT")
    event1.add("uid").value = "uid1"
    event1.add("sequence").value = 1

    event2 = Component("VEVENT")
    event2.add("uid").value = "uid2"
    event2.add("sequence").value = 3
    event2.add("recurrence_id").value = dt.datetime.fromisoformat("1970-01-01T00:00:00Z")

    components = [event1, event2]
    sorted_components = sort_by_uid(components)
    expected_sorted = [event1, event2]
    assert sorted_components == expected_sorted


def test_sort_key():
    event = Component("VEVENT")
    event.add("uid").value = "uid1"
    event.add("sequence").value = 2
    event.add("recurrence_id").value = dt.datetime.fromisoformat("1970-01-01T00:00:00Z")

    sort_key = get_sort_key(event)
    expected_sort_key = "uid1000021970-01-01T00:00:00Z"
    assert sort_key == expected_sort_key
