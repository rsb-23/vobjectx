"""
VObjectx Overview
================
    vobjectx parses vCard or vCalendar files, returning a tree of Python objects.
    It also provids an API to create vCard or vCalendar data structures which
    can then be serialized.

    Parsing existing streams
    ------------------------
    Streams containing one or many L{Component<base.Component>}s can be
    parsed using L{read_components<base.read_components>}.  As each Component
    is parsed, vobjectx will attempt to give it a L{Behavior<behavior.Behavior>}.
    If an appropriate Behavior is found, any base64, quoted-printable, or
    backslash escaped data will automatically be decoded.  Dates and datetimes
    will be transformed to datetime.date or datetime.datetime instances.
    Components containing recurrence information will have a special rruleset
    attribute (a dateutil.rrule.rruleset instance).

    Validation
    ----------
    Behavior classes validate Components. Pass raise_exception=True to raise
    ValidateError on failure, or complain_unrecognized=True to reject unknown children.

    Creating objects programatically
    --------------------------------
    Use iCalendar() and vCard() to create blank top-level components, or
    new_from_behavior(name) for any registered component type.

    Serializing objects
    -------------------
    Serialization:
      - Looks for missing required children that can be automatically generated,
        like a UID or a PRODID, and adds them
      - Encodes all values that can be automatically encoded
      - Checks to make sure the object is valid (unless this behavior is
        explicitly disabled)
      - Appends the serialized object to a buffer, or fills a new
        buffer and returns it

    Examples
    --------

    >>> import datetime
    >>> import dateutil.rrule as rrule
    >>> x = iCalendar()
    >>> x.add('vevent')
    <VEVENT| []>
    >>> x
    <VCALENDAR| [<VEVENT| []>]>
    >>> v = x.vevent
    >>> utc = icalendar.utc
    >>> v.add('dtstart').value = datetime.datetime(2004, 12, 15, 14, tzinfo = utc)
    >>> v
    <VEVENT| [<DTSTART{}2004-12-15 14:00:00+00:00>]>
    >>> x
    <VCALENDAR| [<VEVENT| [<DTSTART{}2004-12-15 14:00:00+00:00>]>]>
    >>> newrule = rrule.rruleset()
    >>> newrule.rrule(rrule.rrule(rrule.WEEKLY, count=2, dtstart=v.dtstart.value))
    >>> v.rruleset = newrule
    >>> list(v.rruleset)
    [datetime.datetime(2004, 12, 15, 14, 0, tzinfo=tzutc()), datetime.datetime(2004, 12, 22, 14, 0, tzinfo=tzutc())]
    >>> v.add('uid').value = "randomuid@MYHOSTNAME"
    >>> print(x.serialize())
    BEGIN:VCALENDAR
    VERSION:2.0
    PRODID:-//VOBJECTX//NONSGML Version 1//EN
    BEGIN:VEVENT
    UID:randomuid@MYHOSTNAME
    DTSTART:20041215T140000Z
    RRULE:FREQ=WEEKLY;COUNT=2
    END:VEVENT
    END:VCALENDAR

"""

from . import icalendar, vcard
from .__about__ import __version__
from .base import read_components, read_one
from .behavior import new_from_behavior

# Package version
VERSION = __version__


# noinspection PyPep8Naming
def iCalendar():  # pylint:disable=invalid-name
    return new_from_behavior("vcalendar", "2.0")


# noinspection PyPep8Naming
def vCard():  # pylint:disable=invalid-name
    return new_from_behavior("vcard", "3.0")


__all__ = ["icalendar", "vcard", "read_components", "read_one", "new_from_behavior", "iCalendar", "vCard", "VERSION"]
