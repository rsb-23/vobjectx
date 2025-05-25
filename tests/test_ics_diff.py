import pytest

from vobject.icalendar import Component
from vobject.ics_diff import get_sort_key, sort_by_uid

# AI generated


def test_empty_list():
    assert sort_by_uid([]) == []


def test_single_component():
    component = Component("VEVENT")
    components = [component]
    sorted_components = sort_by_uid(components)
    expected_sorted = [components[0]]
    assert sorted_components == expected_sorted


@pytest.mark.skip(reason="to be checked")
def test_multiple_components():
    event1 = Component("VEVENT", uid="uid1", sequence=1, recurrence_id=None)
    event2 = Component("VEVENT", uid="uid2", sequence=3, recurrence_id="1970-01-01T00:00:00Z")
    components = [event1, event2]
    sorted_components = sort_by_uid(components)
    expected_sorted = [event1, event2]
    assert sorted_components == expected_sorted


@pytest.mark.skip(reason="to be checked")
def test_sort_key():
    event = Component("VEVENT", uid="uid1", sequence=2, recurrence_id="1970-01-01T00:00:00Z")
    sort_key = get_sort_key(event)
    expected_sort_key = "uid10020000001970-01-01T00:00:00Z"
    assert sort_key == expected_sort_key
