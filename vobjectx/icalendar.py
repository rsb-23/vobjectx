# pylint: disable=c0123,c0302,w0212, r0915
"""Definitions and behavior for iCalendar, also known as vCalendar 2.0"""

from __future__ import annotations

import datetime as dt
import math
import socket

import pytz
from dateutil import rrule, tz

from .__about__ import __version__ as VERSION
from .base import Component, ContentLine, fold_one_line, register_behavior
from .behavior import Behavior
from .exceptions import AllException, NativeError, ParseError, ValidateError, VObjectError
from .helper import backslash_escape, get_buffer, get_random_int, logger, split_delta, to_unicode
from .helper.imports_ import base64, contextlib, partial
from .parser import string_to_durations

# ------------------------------- Constants ------------------------------------
DATENAMES = ("rdate", "exdate")
RULENAMES = ("exrule", "rrule")
DATESANDRULES = ("exrule", "rrule", "rdate", "exdate")
PRODID = f"-//VOBJECTX//NONSGML Version {VERSION}//EN"

WEEKDAYS = "MO", "TU", "WE", "TH", "FR", "SA", "SU"
FREQUENCIES = ("YEARLY", "MONTHLY", "WEEKLY", "DAILY", "HOURLY", "MINUTELY", "SECONDLY")

zero_delta = dt.timedelta(0)
two_hours = dt.timedelta(hours=2)

# ---------------------------- TZID registry -----------------------------------
__tzid_map = {}


def register_tzid(tzid, tzinfo):
    """Register a tzid -> tzinfo mapping."""
    __tzid_map[to_unicode(tzid)] = tzinfo


def get_tzid(tzid, smart=True):
    """Return the tzid if it exists, or None."""
    _tz = __tzid_map.get(to_unicode(tzid))
    if smart and tzid and not _tz:
        try:
            _tz = pytz.timezone(tzid)
            register_tzid(to_unicode(tzid), _tz)
        except pytz.UnknownTimeZoneError as e:
            logger.error(e)
    return _tz


utc = tz.tzutc()
register_tzid("UTC", utc)

# -------------------- Helper subclasses ---------------------------------------
_TRANSITIONS = "daylight", "standard"


def _date_to_datetime(dt_obj: dt.datetime | dt.date):
    if isinstance(dt_obj, dt.datetime):
        return dt_obj
    return dt.datetime.fromordinal(dt_obj.toordinal())


def _from_last_week(dt_):
    """
    How many weeks from the end of the month dt is, starting from 1.
    """
    next_month = dt.datetime(dt_.year, dt_.month + 1, 1)
    time_diff = next_month - dt_
    days_gap = time_diff.days + bool(time_diff.seconds)
    return math.ceil(days_gap / 7)


# noinspection PyProtectedMember
class TimezoneComponent(Component):
    """
    A VTIMEZONE object.

    VTIMEZONEs are parsed by tz.tzical, the resulting dt.tzinfo subclass is stored in self.tzinfo, self.tzid stores
    the TZID associated with this timezone.

    @ivar name:
        The uppercased name of the object, in this case always 'VTIMEZONE'.
    @ivar tzinfo:
        A dt.tzinfo subclass representing this timezone.
    @ivar tzid:
        The string used to refer to this timezone.
    """

    def __init__(self, tzinfo=None, *args, **kwds):
        """
        Accept an existing Component or a tzinfo class.
        """
        super().__init__(*args, **kwds)
        self.is_native = True
        # hack to make sure a behavior is assigned
        if self.behavior is None:
            self.behavior = VTimezone
        if tzinfo is not None:
            self.tzinfo = tzinfo
        if not hasattr(self, "name") or self.name == "":
            self.name = "VTIMEZONE"
            self.use_begin = True

    @classmethod
    def register_tzinfo(cls, tzinfo):
        """
        Register tzinfo if it's not already registered, return its tzid.
        """
        tzid = cls.pick_tzid(tzinfo)
        if tzid and not get_tzid(tzid, False):
            register_tzid(tzid, tzinfo)
        return tzid

    @property
    def tzinfo(self):
        # workaround for dateutil failing to parse some experimental properties
        good_lines = ("rdate", "rrule", "dtstart", "tzname", "tzoffsetfrom", "tzoffsetto", "tzid")
        # serialize encodes as utf-8, cStringIO will leave utf-8 alone
        buffer = get_buffer()
        # allow empty VTIMEZONEs
        if len(self.contents) == 0:
            return None

        def custom_serialize(obj):
            if isinstance(obj, Component):
                fold_one_line(buffer, f"BEGIN:{obj.name}")
                for child in obj.lines():
                    if child.name.lower() in good_lines:
                        child.serialize(buffer, 75, validate=False)
                for comp in obj.components():
                    custom_serialize(comp)
                fold_one_line(buffer, f"END:{obj.name}")

        custom_serialize(self)
        buffer.seek(0)  # tzical wants to read a stream
        return tz.tzical(buffer).get()

    @tzinfo.setter
    def tzinfo(self, tzinfo, start=2000, end=2030):
        # pylint: disable=r0914
        """
        Create appropriate objects in self to represent tzinfo.

        Collapse DST transitions to rrules as much as possible.

        Assumptions:
        - DST <-> Standard transitions occur on the hour
        - never within a month of one another
        - twice or fewer times a year
        - never in the month of December
        - DST always moves offset exactly one hour later
        - tzinfo classes dst method always treats times that could be in either offset as being in the later regime
        """

        # lists of dictionaries defining rules which are no longer in effect
        completed = {"daylight": [], "standard": []}

        # dictionary defining rules which are currently in effect
        working: dict[str, dict | None] = {"daylight": None, "standard": None}

        # rule may be based on nth week of the month or the nth from the last
        for year in range(start, end + 1):
            newyear = dt.datetime(year, 1, 1)
            for transition_to in _TRANSITIONS:
                transition = get_transition(transition_to, year, tzinfo)
                oldrule = working[transition_to]

                if transition == newyear:
                    # transition_to is in effect for the whole year
                    rule = {
                        "end": None,
                        "start": newyear,
                        "month": 1,
                        "weekday": None,
                        "hour": None,
                        "plus": None,
                        "minus": None,
                        "name": tzinfo.tzname(newyear),
                        "offset": tzinfo.utcoffset(newyear),
                        "offsetfrom": tzinfo.utcoffset(newyear),
                    }
                    if oldrule is None:
                        # transition_to was not yet in effect
                        working[transition_to] = rule
                    elif oldrule["offset"] != tzinfo.utcoffset(newyear):
                        # transition_to was already in effect.
                        # old rule was different, it shouldn't continue
                        oldrule["end"] = year - 1
                        completed[transition_to].append(oldrule)
                        working[transition_to] = rule
                elif transition is None:
                    # transition_to is not in effect
                    if oldrule is not None:
                        # transition_to used to be in effect
                        oldrule["end"] = year - 1
                        completed[transition_to].append(oldrule)
                        working[transition_to] = None
                else:
                    # an offset transition was found
                    try:
                        old_offset = tzinfo.utcoffset(transition - two_hours)
                        name = tzinfo.tzname(transition)
                        offset = tzinfo.utcoffset(transition)
                    except (pytz.AmbiguousTimeError, pytz.NonExistentTimeError):
                        # guaranteed that tzinfo is a pytz timezone
                        is_dst = transition_to == "daylight"
                        old_offset = tzinfo.utcoffset(transition - two_hours, is_dst=is_dst)
                        name = tzinfo.tzname(transition, is_dst=is_dst)
                        offset = tzinfo.utcoffset(transition, is_dst=is_dst)

                    rule = {
                        "end": None,  # None, or an integer year
                        "start": transition,  # the datetime of transition
                        "month": transition.month,
                        "weekday": transition.weekday(),
                        "hour": transition.hour,
                        "name": name,
                        "plus": int((transition.day - 1) / 7 + 1),  # nth week of the month
                        "minus": _from_last_week(transition),  # nth from last week
                        "offset": offset,
                        "offsetfrom": old_offset,
                    }

                    if oldrule is None:
                        working[transition_to] = rule
                    else:
                        plus_match = rule["plus"] == oldrule["plus"]
                        minus_match = rule["minus"] == oldrule["minus"]
                        truth = plus_match or minus_match
                        truth = truth and all(
                            rule[key] == oldrule[key] for key in ("month", "weekday", "hour", "offset")
                        )
                        if truth:
                            # the old rule is still true, limit to plus or minus
                            oldrule["plus"] = oldrule["plus"] if plus_match else None
                            oldrule["minus"] = oldrule["minus"] if minus_match else None
                        else:
                            # the new rule did not match the old
                            oldrule["end"] = year - 1
                            completed[transition_to].append(oldrule)
                            working[transition_to] = rule

        for transition_to, rule in working.items():
            if rule is not None:
                completed[transition_to].append(rule)

        self.contents.tzid = []
        self.contents.daylight = []
        self.contents.standard = []

        self.add("tzid").value = self.pick_tzid(tzinfo, True)

        # old = None # unused?
        for transition_to, rules in completed.items():
            for rule in rules:
                comp = self.add(transition_to)
                dtstart = comp.add("dtstart")
                dtstart.value = rule["start"]
                if rule["name"] is not None:
                    comp.add("tzname").value = rule["name"]
                line = comp.add("tzoffsetto")
                line.value = delta_to_offset(rule["offset"])
                line = comp.add("tzoffsetfrom")
                line.value = delta_to_offset(rule["offsetfrom"])

                num = rule["plus"] or -1 * (rule["minus"] or 0)
                day_string = f"BYDAY={num}{WEEKDAYS[rule['weekday']]}" if num else ""

                end_string = ""
                if rule["end"] is not None:
                    # all year offset, with no rule
                    end_date = dt.datetime(rule["end"], 1, 1)
                    if rule["hour"] is not None:
                        du_rule = rrule.rrule(
                            rrule.YEARLY,
                            bymonth=rule["month"],
                            byweekday=rrule.weekday(rule["weekday"], num),
                            dtstart=dt.datetime(rule["end"], 1, 1, rule["hour"]),
                        )
                        end_date = du_rule[0]
                    end_date = end_date.replace(tzinfo=utc) - rule["offsetfrom"]
                    end_string = f"UNTIL={datetime_to_string(end_date)}"

                new_rule = ";".join(["FREQ=YEARLY", day_string, f"BYMONTH={rule['month']}", end_string])
                comp.add("rrule").value = new_rule.strip(";")

    @staticmethod
    def pick_tzid(tzinfo, allow_utc=False):
        """
        Given a tzinfo class, use known APIs to determine TZID, or use tzname.
        """
        if tzinfo is None or (not allow_utc and tzinfo_eq(tzinfo, utc)):
            # If tzinfo is UTC, we don't need a TZID
            return None

        for attr in ("tzid", "zone", "_tzid"):
            tzid_ = getattr(tzinfo, attr, None)
            if tzid_:
                return to_unicode(tzid_)

        # return tzname for standard (non-DST) time
        not_dst = dt.timedelta(0)
        for month in range(1, 13):
            _dt = dt.datetime(2000, month, 1)
            if tzinfo.dst(_dt) == not_dst:
                return to_unicode(tzinfo.tzname(_dt))

        # there was no standard time in 2000!
        raise VObjectError(f"Unable to guess TZID for tzinfo {tzinfo!s}")

    def __repr__(self):
        return f'<VTIMEZONE | {getattr(self, "tzid", "No TZID")}>'

    def pretty_print(self, level=0, tabwidth=3):
        pre = " " * level * tabwidth
        print(pre, self.name)
        print(pre, "TZID:", self.tzid)
        print("")


# noinspection PyProtectedMember
class RecurringComponent(Component):
    """
    A vCalendar component like VEVENT or VTODO which may recur.

    Any recurring component can have one or multiple RRULE, RDATE, EXRULE, or EXDATE lines, and one or zero DTSTART
    lines. It can also have a variety of children that don't have any recurrence information.

    In the example below, note that dtstart is included in the rruleset. This is not the default behavior for
    dateutil's rrule implementation unless dtstart would already have been a member of the recurrence rule,
    and as a result, COUNT is wrong. This can be worked around when getting rruleset by adjusting count down by one
    if an rrule has a count and dtstart isn't in its result set, but by default, the rruleset property doesn't do
    this work around, to access it getrruleset must be called with addRDate set True.

    @property rruleset:
        A U{rruleset<https://moin.conectiva.com.br/DateUtil>}.
    """

    def __init__(self, *args, **kwds):
        super().__init__(*args, **kwds)
        self.is_native = True

    @property
    def rruleset(self):
        return self.getrruleset()

    def getrruleset(self, add_rdate=False):
        """
        Get an rruleset created from self.

        If addRDate is True, add an RDATE for dtstart if it's not included in an RRULE or RDATE, and count is
        decremented if it exists.

        Note that for rules which don't match DTSTART, DTSTART may not appear in list(rruleset), although it should.
        By default, an RDATE is not created in these cases, and count isn't updated, so dateutil may list a spurious
        occurrence.
        """
        rruleset = None
        for name in DATESANDRULES:
            addfunc = None
            for line in self.contents.get(name, ()):
                # don't bother creating a rruleset unless there's a rule
                rruleset = rruleset or rrule.rruleset()
                addfunc = addfunc or getattr(rruleset, name)

                try:
                    dtstart = self.dtstart.value
                except (AttributeError, KeyError):
                    # Special for VTODO - try DUE property instead
                    if self.name != "VTODO":
                        # if there's no dtstart, just return None
                        logger.error("failed to get dtstart with VTODO")
                        return None

                    try:
                        dtstart = self.due.value
                    except (AttributeError, KeyError):
                        # if there's no due, just return None
                        logger.error("failed to find DUE at all.")
                        return None

                if name in DATENAMES:
                    # ignoring RDATEs with PERIOD values for now
                    for _dt in line.value:
                        addfunc(_date_to_datetime(_dt))
                elif name in RULENAMES:
                    # a Ruby iCalendar library escapes semi-colons in rrules, so also remove any backslashes
                    value = line.value.replace("\\", "")
                    # If dtstart has no time zone, `until` shouldn't get one, either:
                    ignoretz = not isinstance(dtstart, dt.datetime) or dtstart.tzinfo is None
                    try:
                        until = rrule.rrulestr(value, ignoretz=ignoretz)._until
                    except ValueError:
                        # WORKAROUND: dateutil<=2.7.2 doesn't set the time zone of dtstart
                        if ignoretz:
                            raise
                        utc_now = dt.datetime.now(dt.timezone.utc)
                        until = rrule.rrulestr(value, dtstart=utc_now)._until

                    if until is not None and isinstance(dtstart, dt.datetime) and (until.tzinfo != dtstart.tzinfo):
                        # dateutil converts the UNTIL date to a datetime,
                        # check to see if the UNTIL parameter value was a date
                        vals = dict(pair.split("=") for pair in value.upper().split(";"))
                        if len(vals.get("UNTIL", "")) == 8:
                            until = dt.datetime.combine(until.date(), dtstart.time())
                        # While RFC2445 says UNTIL MUST be UTC, Chandler allows floating recurring events, and uses
                        # floating UNTIL values. Also, some odd floating UNTIL but timezoned DTSTART values have
                        # shown up in the wild, so put floating UNTIL values DTSTART's timezone
                        if until.tzinfo is None:
                            until = until.replace(tzinfo=dtstart.tzinfo)

                        # RFC2445 actually states that UNTIL must be a UTC value. Whilst the changes above work OK,
                        # one problem case is if DTSTART is floating but UNTIL is properly specified as UTC (or with
                        # a TZID). In that case dateutil will fail datetime comparisons. There is no easy solution to
                        # this as there is no obvious timezone (at this point) to do proper floating time offset
                        # comparisons. The best we can do is treat the UNTIL value as floating. This could mean
                        # incorrect determination of the last instance. The better solution here is to encourage
                        # clients to use COUNT rather than UNTIL when DTSTART is floating.

                        until = (
                            until.replace(tzinfo=None) if dtstart.tzinfo is None else until.astimezone(dtstart.tzinfo)
                        )

                    value_without_until = ";".join(
                        pair for pair in value.split(";") if pair.split("=")[0].upper() != "UNTIL"
                    )
                    rule = rrule.rrulestr(value_without_until, dtstart=dtstart, ignoretz=ignoretz)
                    rule._until = until

                    # add the rrule or exrule to the rruleset
                    addfunc(rule)

                if name in ["rrule", "rdate"] and add_rdate:
                    # rlist = rruleset._rrule if name == 'rrule' else rruleset._rdate

                    # dateutils does not work with all-day (dt.date) items so we need to convert to a
                    # dt.datetime (which is what dateutils does internally)
                    adddtstart = _date_to_datetime(dtstart)

                    try:  # sourcery skip
                        if name == "rrule":
                            if rruleset._rrule[-1][0] != adddtstart:
                                rruleset.rdate(adddtstart)

                                if rruleset._rrule[-1]._count is not None:
                                    rruleset._rrule[-1]._count -= 1

                        elif name == "rdate":
                            if rruleset._rdate[0] != adddtstart:
                                rruleset.rdate(adddtstart)
                    except IndexError:
                        # it's conceivable that an rrule has 0 datetimes
                        pass

        return rruleset

    @rruleset.setter
    def rruleset(self, rruleset):
        def _parse_values_from_rule(rule) -> dict:
            _value_map = {"BYYEARDAY": rule._byyearday, "BYWEEKNO": rule._byweekno, "BYSETPOS": rule._bysetpos}
            values_ = {}
            for k, v in _value_map.items():
                if v is not None:
                    values_[k] = [str(n) for n in v]

            if rule._interval != 1:
                values_["INTERVAL"] = [str(rule._interval)]
            if rule._wkst != 0:  # wkst defaults to Monday
                values_["WKST"] = [WEEKDAYS[rule._wkst]]

            if rule._count is not None:
                values_["COUNT"] = [str(rule._count)]
            elif rule._until is not None:
                values_["UNTIL"] = [until_serialize(rule._until)]

            days = []
            if rule._byweekday is not None and (
                rrule.WEEKLY != rule._freq or len(rule._byweekday) != 1 or rule._dtstart.weekday() != rule._byweekday[0]
            ):
                # ignore byweekday if freq is WEEKLY and day correlates with dtstart because
                # it was automatically set by dateutil
                days.extend(WEEKDAYS[n] for n in rule._byweekday)

            if rule._bynweekday is not None:
                days.extend(n + WEEKDAYS[day] for day, n in rule._bynweekday)

            if days:
                values_["BYDAY"] = days

            if rule._bymonthday and not (
                rule._freq <= rrule.MONTHLY and len(rule._bymonthday) == 1 and rule._bymonthday[0] == rule._dtstart.day
            ):
                # ignore bymonthday if it's generated by dateutil
                values_["BYMONTHDAY"] = [str(n) for n in rule._bymonthday]

            if rule._bynmonthday:
                values_.setdefault("BYMONTHDAY", []).extend(str(n) for n in rule._bynmonthday)

            if rule._bymonth and (
                rule._byweekday
                or not (
                    rule._freq == rrule.YEARLY and len(rule._bymonth) == 1 and rule._bymonth[0] == rule._dtstart.month
                )
            ):
                # ignore bymonth if it's generated by dateutil
                values_["BYMONTH"] = [str(n) for n in rule._bymonth]

            # byhour, byminute, bysecond are always ignored for now
            return values_

        # Get DTSTART from component (or DUE if no DTSTART in a VTODO)
        try:
            dtstart = self.dtstart.value
        except (AttributeError, KeyError):
            if self.name != "VTODO":
                raise
            dtstart = self.due.value

        is_date = type(dtstart) is dt.date

        dtstart = _date_to_datetime(dtstart)
        # make sure to convert time zones to UTC
        until_serialize = date_to_string if is_date else partial(datetime_to_string, convert_to_utc=True)

        for name in DATESANDRULES:
            if name in self.contents:
                del self.contents[name]
            setlist = getattr(rruleset, f"_{name}")
            if name in DATENAMES:
                setlist = list(setlist)  # make a copy of the list
                if name == "rdate" and dtstart in setlist:
                    setlist.remove(dtstart)
                if is_date:
                    setlist = [_dt.date() for _dt in setlist]
                if setlist:
                    self.add(name).value = setlist
            elif name in RULENAMES:
                for rule_item in setlist:
                    buf = get_buffer()
                    buf.write(f"FREQ={FREQUENCIES[rule_item._freq]}")

                    values = _parse_values_from_rule(rule_item)
                    for key, paramvals in values.items():
                        buf.write(f";{key}={','.join(paramvals)}")

                    self.add(name).value = buf.getvalue()


class TextBehavior(Behavior):
    """
    Provide backslash escape encoding/decoding for single valued properties.

    TextBehavior also deals with base64 encoding if the ENCODING parameter is explicitly set to BASE64.
    """

    base64string = "BASE64"  # vCard uses B

    @classmethod
    def decode(cls, line):
        """
        Remove backslash escaping from line.value.
        """
        if line.encoded:
            encoding = getattr(line, "encoding_param", None)
            if encoding and encoding.upper() == cls.base64string:
                line.value = base64.b64decode(line.value)
            else:
                line.value = string_to_text_values(line.value)[0]
            line.encoded = False

    @classmethod
    def encode(cls, line):
        """
        Backslash escape line.value.
        """
        if not line.encoded:
            encoding = getattr(line, "encoding_param", None)
            if encoding and encoding.upper() == cls.base64string:
                line.value = base64.b64encode(line.value.encode("utf-8")).decode("utf-8").replace("\n", "")
            else:
                line.value = backslash_escape(line.value)
            line.encoded = True


class VCalendarComponentBehavior(Behavior):
    default_behavior = TextBehavior
    is_component = True


class RecurringBehavior(VCalendarComponentBehavior):
    """
    Parent Behavior for components which should be RecurringComponents.
    """

    has_native = True

    @staticmethod
    def transform_to_native(obj):
        """
        Turn a recurring Component into a RecurringComponent.
        """
        if not obj.is_native:
            object.__setattr__(obj, "__class__", RecurringComponent)
            obj.is_native = True
        return obj

    @staticmethod
    def transform_from_native(obj):
        if obj.is_native:
            object.__setattr__(obj, "__class__", Component)
            obj.is_native = False
        return obj

    @staticmethod
    def generate_implicit_parameters(obj):
        """
        Generate a UID and DTSTAMP if one does not exist.

        This is just a dummy implementation, for now.
        """
        if not hasattr(obj, "uid"):
            now = dt.datetime.now(utc)
            now = datetime_to_string(now)
            host = socket.gethostname()
            obj.add(ContentLine("UID", [], f"{now} - {get_random_int()}@{host}"))

        if not hasattr(obj, "dtstamp"):
            now = dt.datetime.now(utc)
            obj.add("dtstamp").value = now


class DateTimeBehavior(Behavior):
    """
    Parent Behavior for ContentLines containing one DATE-TIME.
    """

    has_native = True

    @staticmethod
    def transform_to_native(obj):
        """
        Turn obj.value into a dt.

        RFC2445 allows times without time zone information, "floating times" in some properties. Mostly, this isn't
        what you want, but when parsing a file, real floating times are noted by setting to 'TRUE' the
        X-VOBJ-FLOATINGTIME-ALLOWED parameter.
        """
        if obj.is_native:
            return obj
        obj.is_native = True
        if obj.value == "":
            return obj
        obj.value = obj.value
        # we're cheating a little here, parse_dtstart allows DATE
        obj.value = parse_dtstart(obj)
        if obj.value.tzinfo is None:
            obj.params["X-VOBJ-FLOATINGTIME-ALLOWED"] = ["TRUE"]
        if obj.params.get("TZID"):
            # Keep a copy of the original TZID around
            obj.params["X-VOBJ-ORIGINAL-TZID"] = [obj.params.pop("TZID")]
        return obj

    @classmethod
    def transform_from_native(cls, obj):
        """
        Replace the datetime in obj.value with an ISO 8601 string.
        """
        if obj.is_native:
            obj.is_native = False
            tzid = TimezoneComponent.register_tzinfo(obj.value.tzinfo)
            obj_value: str | dt.datetime = datetime_to_string(obj.value, cls.force_utc)
            if not cls.force_utc and tzid is not None:
                obj.tzid_param = tzid
            if obj.params.get("X-VOBJ-ORIGINAL-TZID"):
                if not hasattr(obj, "tzid_param"):
                    obj.tzid_param = obj.x_vobj_original_tzid_param
                del obj.params["X-VOBJ-ORIGINAL-TZID"]
            obj.value = obj_value
        return obj


class UTCDateTimeBehavior(DateTimeBehavior):
    """
    A value which must be specified in UTC.
    """

    force_utc = True


class DateOrDateTimeBehavior(Behavior):
    """
    Parent Behavior for ContentLines containing one DATE or DATE-TIME.
    """

    has_native = True

    @staticmethod
    def transform_to_native(obj):
        """
        Turn obj.value into a date or dt.
        """
        if obj.is_native:
            return obj
        obj.is_native = True
        if obj.value == "":
            return obj
        obj.value = obj.value
        obj.value = parse_dtstart(obj, allow_signature_mismatch=True)
        if getattr(obj, "value_param", "DATE-TIME").upper() == "DATE-TIME" and hasattr(obj, "tzid_param"):
            # Keep a copy of the original TZID around
            obj.params["X-VOBJ-ORIGINAL-TZID"] = [obj.tzid_param]
            del obj.tzid_param
        return obj

    @staticmethod
    def transform_from_native(obj):
        """
        Replace the date or datetime in obj.value with an ISO 8601 string.
        """
        if type(obj.value) is not dt.date:
            return DateTimeBehavior.transform_from_native(obj)
        obj.is_native = False
        obj.value_param = "DATE"
        obj.value = date_to_string(obj.value)
        return obj


class MultiDateBehavior(Behavior):
    """
    Parent Behavior for ContentLines containing one or more DATE, DATE-TIME, or PERIOD.
    """

    has_native = True

    @staticmethod
    def transform_to_native(obj):
        """
        Turn obj.value into a list of dates, datetimes, or (datetime, timedelta) tuples.
        """
        if obj.is_native:
            return obj
        obj.is_native = True
        if obj.value == "":
            obj.value = []
            return obj
        tzinfo = get_tzid(getattr(obj, "tzid_param", None))
        value_param = getattr(obj, "value_param", "DATE-TIME").upper()
        val_texts = obj.value.split(",")
        if value_param == "DATE":
            obj.value = [string_to_date(x) for x in val_texts]
        elif value_param == "DATE-TIME":
            obj.value = [string_to_date_time(x, tzinfo) for x in val_texts]
        elif value_param == "PERIOD":
            obj.value = [string_to_period(x, tzinfo) for x in val_texts]
        return obj

    @staticmethod
    def transform_from_native(obj):
        """
        Replace the date, datetime or period tuples in obj.value with appropriate strings.
        """
        if obj.value and type(obj.value[0]) is dt.date:
            obj.is_native = False
            obj.value_param = "DATE"
            obj.value = ",".join([date_to_string(val) for val in obj.value])

        # Fixme: handle PERIOD case
        elif obj.is_native:
            obj.is_native = False
            transformed = []
            tzid = None
            for val in obj.value:
                if tzid is None and type(val) is dt.datetime:
                    tzid = TimezoneComponent.register_tzinfo(val.tzinfo)
                    if tzid is not None:
                        obj.tzid_param = tzid
                transformed.append(datetime_to_string(val))
            obj.value = ",".join(transformed)
        return obj


class MultiTextBehavior(Behavior):
    """
    Provide backslash escape encoding/decoding of each of several values.

    After transformation, value is a list of strings.
    """

    list_separator = ","

    @classmethod
    def decode(cls, line):
        """
        Remove backslash escaping from line.value, then split on commas.
        """
        if line.encoded:
            line.value = string_to_text_values(line.value, list_separator=cls.list_separator)
            line.encoded = False

    @classmethod
    def encode(cls, line):
        """
        Backslash escape line.value.
        """
        if not line.encoded:
            line.value = cls.list_separator.join(backslash_escape(val) for val in line.value)
            line.encoded = True


class SemicolonMultiTextBehavior(MultiTextBehavior):
    list_separator = ";"


# ------------------------ Registered Behavior subclasses ----------------------
class VCalendar2(VCalendarComponentBehavior):
    """
    vCalendar 2.0 behavior. With added VAVAILABILITY support.
    """

    name = "VCALENDAR"
    description = "vCalendar 2.0, also known as iCalendar."
    version_string = "2.0"
    sort_first = ("version", "calscale", "method", "prodid", "vtimezone")
    known_children = {
        "CALSCALE": (0, 1, None),  # min, max, behavior_registry id
        "METHOD": (0, 1, None),
        "VERSION": (0, 1, None),  # required, but auto-generated
        "PRODID": (1, 1, None),
        "VTIMEZONE": (0, None, None),
        "VEVENT": (0, None, None),
        "VTODO": (0, None, None),
        "VJOURNAL": (0, None, None),
        "VFREEBUSY": (0, None, None),
        "VAVAILABILITY": (0, None, None),
    }

    @classmethod
    def generate_implicit_parameters(cls, obj):
        """
        Create PRODID, VERSION and VTIMEZONEs if needed.

        VTIMEZONEs will need to exist whenever TZID parameters exist or when datetimes with tzinfo exist.
        """
        for comp in obj.components():
            if comp.behavior is not None:
                comp.behavior.generate_implicit_parameters(comp)
        if not hasattr(obj, "prodid"):
            obj.add(ContentLine("PRODID", [], PRODID))
        if not hasattr(obj, "version"):
            obj.add(ContentLine("VERSION", [], cls.version_string))
        tzids_used = {}

        def find_tzids(obj_, table):
            if isinstance(obj_, ContentLine) and (obj_.behavior is None or not obj_.behavior.force_utc):
                if getattr(obj_, "tzid_param", None):
                    table[obj_.tzid_param] = 1
                else:
                    if type(obj_.value) is list:
                        for _ in obj_.value:
                            tzinfo = getattr(obj_.value, "tzinfo", None)
                            tzid_ = TimezoneComponent.register_tzinfo(tzinfo)
                            if tzid_:
                                table[tzid_] = 1
                    else:
                        tzinfo = getattr(obj_.value, "tzinfo", None)
                        tzid_ = TimezoneComponent.register_tzinfo(tzinfo)
                        if tzid_:
                            table[tzid_] = 1
            for child in obj_.get_children():
                if obj_.name != "VTIMEZONE":
                    find_tzids(child, table)

        find_tzids(obj, tzids_used)
        oldtzids = [to_unicode(x.tzid.value) for x in getattr(obj, "vtimezone_list", [])]
        for tzid in tzids_used:
            tzid = to_unicode(tzid)
            if tzid != "UTC" and tzid not in oldtzids:
                obj.add(TimezoneComponent(tzinfo=get_tzid(tzid)))

    @classmethod
    def serialize(cls, obj, buf, line_length, validate=True, *args, **kwargs):
        """
        Set implicit parameters, do encoding, return unicode string.

        If validate is True, raise VObjectError if the line doesn't validate after implicit parameters are generated.

        Default is to call base.default_serialize.
        """

        cls.generate_implicit_parameters(obj)
        if validate:
            cls.validate(obj, raise_exception=True)

        undo_transform = bool(obj.is_native)

        outbuf = buf or get_buffer()
        group_string = "" if obj.group is None else f"{obj.group}."
        if obj.use_begin:
            fold_one_line(outbuf, f"{group_string}BEGIN:{obj.name}", line_length)

        try:
            first_props = [
                s for s in cls.sort_first if s in obj.contents and not isinstance(obj.contents[s][0], Component)
            ]
            first_components = [
                s for s in cls.sort_first if s in obj.contents and isinstance(obj.contents[s][0], Component)
            ]
        except AllException:
            first_props = first_components = []
            # first_components = []

        prop_keys = sorted(
            [k for k in obj.contents.keys() if k not in first_props and not isinstance(obj.contents[k][0], Component)]
        )
        comp_keys = sorted(
            [k for k in obj.contents.keys() if k not in first_components and isinstance(obj.contents[k][0], Component)]
        )

        sorted_keys = first_props + prop_keys + first_components + comp_keys
        children = [o for k in sorted_keys for o in obj.contents[k]]

        for child in children:
            # validate is recursive, we only need to validate once
            child.serialize(outbuf, line_length, validate=False)
        if obj.use_begin:
            fold_one_line(outbuf, f"{group_string}END:{obj.name}", line_length)
        out = buf or outbuf.getvalue()
        if undo_transform:
            obj.transform_to_native()
        return out


VCalendar2_0 = VCalendar2  # alias #pylint:disable=invalid-name
VCalendar2_0.name = "VCALENDAR"
register_behavior(VCalendar2_0)


class VTimezone(VCalendarComponentBehavior):
    """
    Timezone behavior.
    """

    name = "VTIMEZONE"
    has_native = True
    description = "A grouping of component properties that defines a time zone."
    sort_first = ("tzid", "last-modified", "tzurl", "standard", "daylight")
    known_children = {
        "TZID": (1, 1, None),  # min, max, behavior_registry id
        "LAST-MODIFIED": (0, 1, None),
        "TZURL": (0, 1, None),
        "STANDARD": (0, None, None),  # NOTE: One of Standard or
        "DAYLIGHT": (0, None, None),  # Daylight must appear
    }

    @classmethod
    def validate(cls, obj, raise_exception=False, complain_unrecognized=False):
        if not hasattr(obj, "tzid") or obj.tzid.value is None:
            if raise_exception:
                raise ValidateError("VTIMEZONE components must contain a valid TZID")
            return False
        if "standard" in obj.contents or "daylight" in obj.contents:
            return super().validate(obj, raise_exception, complain_unrecognized)

        if raise_exception:
            raise ValidateError("VTIMEZONE components must contain a STANDARD or a DAYLIGHT component")
        return False

    @staticmethod
    def transform_to_native(obj):
        if not obj.is_native:
            object.__setattr__(obj, "__class__", TimezoneComponent)
            obj.is_native = True
            obj.register_tzinfo(obj.tzinfo)
        return obj

    @staticmethod
    def transform_from_native(obj):
        return obj


register_behavior(VTimezone)


class TZID(Behavior):
    """
    Don't use TextBehavior for TZID.

    RFC2445 only allows TZID lines to be paramtext, so they shouldn't need any encoding or decoding.  Unfortunately,
    some Microsoft products use commas in TZIDs which should NOT be treated as a multi-valued text property,
    nor do we want to escape them.  Leaving them alone works for Microsoft's breakage, and doesn't affect compliant
    iCalendar streams.
    """


register_behavior(TZID)


class DaylightOrStandard(VCalendarComponentBehavior):
    has_native = False
    known_children = {"DTSTART": (1, 1, None), "RRULE": (0, 1, None)}  # min, max, behavior_registry id


register_behavior(DaylightOrStandard, "STANDARD")
register_behavior(DaylightOrStandard, "DAYLIGHT")


class VEvent(RecurringBehavior):
    """Event behavior."""

    name = "VEVENT"
    sort_first = ("uid", "recurrence-id", "dtstart", "duration", "dtend")

    description = 'A grouping of component properties, and possibly including \
                   "VALARM" calendar components, that represents a scheduled \
                   amount of time on a calendar.'
    known_children = {
        "DTSTART": (0, 1, None),  # min, max, behavior_registry id
        "CLASS": (0, 1, None),
        "CREATED": (0, 1, None),
        "DESCRIPTION": (0, 1, None),
        "GEO": (0, 1, None),
        "LAST-MODIFIED": (0, 1, None),
        "LOCATION": (0, 1, None),
        "ORGANIZER": (0, 1, None),
        "PRIORITY": (0, 1, None),
        "DTSTAMP": (1, 1, None),  # required
        "SEQUENCE": (0, 1, None),
        "STATUS": (0, 1, None),
        "SUMMARY": (0, 1, None),
        "TRANSP": (0, 1, None),
        "UID": (1, 1, None),
        "URL": (0, 1, None),
        "RECURRENCE-ID": (0, 1, None),
        "DTEND": (0, 1, None),  # NOTE: Only one of DtEnd or
        "DURATION": (0, 1, None),  # Duration can appear
        "ATTACH": (0, None, None),
        "ATTENDEE": (0, None, None),
        "CATEGORIES": (0, None, None),
        "COMMENT": (0, None, None),
        "CONTACT": (0, None, None),
        "EXDATE": (0, None, None),
        "EXRULE": (0, None, None),
        "REQUEST-STATUS": (0, None, None),
        "RELATED-TO": (0, None, None),
        "RESOURCES": (0, None, None),
        "RDATE": (0, None, None),
        "RRULE": (0, None, None),
        "VALARM": (0, None, None),
    }

    @classmethod
    def validate(cls, obj, raise_exception=False, complain_unrecognized=False):
        if "dtend" not in obj.contents or "duration" not in obj.contents:
            return super().validate(obj, raise_exception, complain_unrecognized)
        if raise_exception:
            raise ValidateError("VEVENT components cannot contain both DTEND and DURATION components")
        return False


register_behavior(VEvent)


class VTodo(RecurringBehavior):
    """To-do behavior."""

    name = "VTODO"
    description = 'A grouping of component properties and possibly "VALARM" \
                   calendar components that represent an action-item or \
                   assignment.'
    known_children = {
        "DTSTART": (0, 1, None),  # min, max, behavior_registry id
        "CLASS": (0, 1, None),
        "COMPLETED": (0, 1, None),
        "CREATED": (0, 1, None),
        "DESCRIPTION": (0, 1, None),
        "GEO": (0, 1, None),
        "LAST-MODIFIED": (0, 1, None),
        "LOCATION": (0, 1, None),
        "ORGANIZER": (0, 1, None),
        "PERCENT": (0, 1, None),
        "PRIORITY": (0, 1, None),
        "DTSTAMP": (1, 1, None),
        "SEQUENCE": (0, 1, None),
        "STATUS": (0, 1, None),
        "SUMMARY": (0, 1, None),
        "UID": (0, 1, None),
        "URL": (0, 1, None),
        "RECURRENCE-ID": (0, 1, None),
        "DUE": (0, 1, None),  # NOTE: Only one of Due or
        "DURATION": (0, 1, None),  # Duration can appear
        "ATTACH": (0, None, None),
        "ATTENDEE": (0, None, None),
        "CATEGORIES": (0, None, None),
        "COMMENT": (0, None, None),
        "CONTACT": (0, None, None),
        "EXDATE": (0, None, None),
        "EXRULE": (0, None, None),
        "REQUEST-STATUS": (0, None, None),
        "RELATED-TO": (0, None, None),
        "RESOURCES": (0, None, None),
        "RDATE": (0, None, None),
        "RRULE": (0, None, None),
        "VALARM": (0, None, None),
    }

    @classmethod
    def validate(cls, obj, raise_exception=False, complain_unrecognized=False):
        if "due" not in obj.contents or "duration" not in obj.contents:
            return super().validate(obj, raise_exception, complain_unrecognized)
        if raise_exception:
            raise ValidateError("VTODO components cannot contain both DUE and DURATION components")
        return False


register_behavior(VTodo)


class VJournal(RecurringBehavior):
    """
    Journal entry behavior.
    """

    name = "VJOURNAL"
    known_children = {
        "DTSTART": (0, 1, None),  # min, max, behavior_registry id
        "CLASS": (0, 1, None),
        "CREATED": (0, 1, None),
        "DESCRIPTION": (0, 1, None),
        "LAST-MODIFIED": (0, 1, None),
        "ORGANIZER": (0, 1, None),
        "DTSTAMP": (1, 1, None),
        "SEQUENCE": (0, 1, None),
        "STATUS": (0, 1, None),
        "SUMMARY": (0, 1, None),
        "UID": (0, 1, None),
        "URL": (0, 1, None),
        "RECURRENCE-ID": (0, 1, None),
        "ATTACH": (0, None, None),
        "ATTENDEE": (0, None, None),
        "CATEGORIES": (0, None, None),
        "COMMENT": (0, None, None),
        "CONTACT": (0, None, None),
        "EXDATE": (0, None, None),
        "EXRULE": (0, None, None),
        "REQUEST-STATUS": (0, None, None),
        "RELATED-TO": (0, None, None),
        "RDATE": (0, None, None),
        "RRULE": (0, None, None),
    }


register_behavior(VJournal)


class VFreeBusy(VCalendarComponentBehavior):
    """
    Free/busy state behavior.
    """

    name = "VFREEBUSY"
    description = "A grouping of component properties that describe either a \
                   request for free/busy time, describe a response to a request \
                   for free/busy time or describe a published set of busy time."
    sort_first = ("uid", "dtstart", "duration", "dtend")
    known_children = {
        "DTSTART": (0, 1, None),  # min, max, behavior_registry id
        "CONTACT": (0, 1, None),
        "DTEND": (0, 1, None),
        "DURATION": (0, 1, None),
        "ORGANIZER": (0, 1, None),
        "DTSTAMP": (1, 1, None),
        "UID": (0, 1, None),
        "URL": (0, 1, None),
        "ATTENDEE": (0, None, None),
        "COMMENT": (0, None, None),
        "FREEBUSY": (0, None, None),
        "REQUEST-STATUS": (0, None, None),
    }


register_behavior(VFreeBusy)


class VAlarm(VCalendarComponentBehavior):
    """
    Alarm behavior.
    """

    name = "VALARM"
    description = "Alarms describe when and how to provide alerts about events and to-dos."
    known_children = {
        "ACTION": (1, 1, None),  # min, max, behavior_registry id
        "TRIGGER": (1, 1, None),
        "DURATION": (0, 1, None),
        "REPEAT": (0, 1, None),
        "DESCRIPTION": (0, 1, None),
    }

    @staticmethod
    def generate_implicit_parameters(obj):
        """
        Create default ACTION and TRIGGER if they're not set.
        """
        try:
            obj.action
        except AttributeError:
            obj.add("action").value = "AUDIO"
        try:
            obj.trigger
        except AttributeError:
            obj.add("trigger").value = dt.timedelta(0)

    @classmethod
    def validate(cls, obj, raise_exception=False, complain_unrecognized=False):
        """
        # TODO
        if obj.contents.has_key('dtend') and obj.contents.has_key('duration'):
            if raise_exception:
                raise ValidateError("VEVENT components cannot contain both DTEND and DURATION components")
            return False
        else:
            return super().validate(obj, raise_exception, *args)
        """
        return True


register_behavior(VAlarm)


class VAvailability(VCalendarComponentBehavior):
    """
    Availability state behavior.

    Used to represent user's available time slots.
    """

    name = "VAVAILABILITY"
    description = "A component used to represent a user's available time slots."
    sort_first = ("uid", "dtstart", "duration", "dtend")
    known_children = {
        "UID": (1, 1, None),  # min, max, behavior_registry id
        "DTSTAMP": (1, 1, None),
        "BUSYTYPE": (0, 1, None),
        "CREATED": (0, 1, None),
        "DTSTART": (0, 1, None),
        "LAST-MODIFIED": (0, 1, None),
        "ORGANIZER": (0, 1, None),
        "SEQUENCE": (0, 1, None),
        "SUMMARY": (0, 1, None),
        "URL": (0, 1, None),
        "DTEND": (0, 1, None),
        "DURATION": (0, 1, None),
        "CATEGORIES": (0, None, None),
        "COMMENT": (0, None, None),
        "CONTACT": (0, None, None),
        "AVAILABLE": (0, None, None),
    }

    @classmethod
    def validate(cls, obj, raise_exception=False, complain_unrecognized=False):
        if "dtend" not in obj.contents or "duration" not in obj.contents:
            return super().validate(obj, raise_exception, complain_unrecognized)
        if raise_exception:
            raise ValidateError("VAVAILABILITY components cannot contain both DTEND and DURATION components")
        return False


register_behavior(VAvailability)


class Available(RecurringBehavior):
    """
    Event behavior.
    """

    name = "AVAILABLE"
    sort_first = ("uid", "recurrence-id", "dtstart", "duration", "dtend")
    description = "Defines a period of time in which a user is normally available."
    known_children = {
        "DTSTAMP": (1, 1, None),  # min, max, behavior_registry id
        "DTSTART": (1, 1, None),
        "UID": (1, 1, None),
        "DTEND": (0, 1, None),  # NOTE: One of DtEnd or
        "DURATION": (0, 1, None),  # Duration must appear, but not both
        "CREATED": (0, 1, None),
        "LAST-MODIFIED": (0, 1, None),
        "RECURRENCE-ID": (0, 1, None),
        "RRULE": (0, 1, None),
        "SUMMARY": (0, 1, None),
        "CATEGORIES": (0, None, None),
        "COMMENT": (0, None, None),
        "CONTACT": (0, None, None),
        "EXDATE": (0, None, None),
        "RDATE": (0, None, None),
    }

    @classmethod
    def validate(cls, obj, raise_exception=False, complain_unrecognized=False):
        if ("dtend" in obj.contents) ^ ("duration" in obj.contents):
            return super().validate(obj, raise_exception, complain_unrecognized)
        if raise_exception:
            raise ValidateError("AVAILABLE components must have either DTEND or DURATION properties, but not both")
        return False


register_behavior(Available)


class Duration(Behavior):
    """
    Behavior for Duration ContentLines.  Transform to dt.timedelta.
    """

    name = "DURATION"
    has_native = True

    @staticmethod
    def transform_to_native(obj):
        """
        Turn obj.value into a dt.timedelta.
        """
        if obj.is_native:
            return obj
        obj.is_native = True
        obj.value = obj.value
        if obj.value == "":
            return obj

        deltalist = string_to_durations(obj.value)
        # When can DURATION have multiple durations?  For now:
        if len(deltalist) == 1:
            obj.value = deltalist[0]
            return obj

        raise ParseError("DURATION must have a single duration string.")

    @staticmethod
    def transform_from_native(obj):
        """
        Replace the dt.timedelta in obj.value with an RFC2445 string.
        """
        if not obj.is_native:
            return obj
        obj.is_native = False
        obj.value = timedelta_to_string(obj.value)
        return obj


register_behavior(Duration)


class Trigger(Behavior):
    """
    DATE-TIME or DURATION
    """

    name = "TRIGGER"
    description = "This property specifies when an alarm will trigger."
    has_native = True
    force_utc = True

    @staticmethod
    def transform_to_native(obj):
        """
        Turn obj.value into a timedelta or dt.
        """
        if obj.is_native:
            return obj
        value = getattr(obj, "value_param", "DURATION").upper()
        if hasattr(obj, "value_param"):
            del obj.value_param
        if obj.value == "":
            obj.is_native = True
            return obj
        if value == "DURATION":
            try:
                return Duration.transform_to_native(obj)
            except ParseError:
                logger.warning(
                    "TRIGGER not recognized as DURATION, trying DATE-TIME, because iCal sometimes exports DATE-TIMEs "
                    "without setting VALUE=DATE-TIME"
                )
                try:
                    obj.is_native = False
                    return DateTimeBehavior.transform_to_native(obj)
                except AllException as e:
                    raise ParseError("TRIGGER with no VALUE not recognized as DURATION or as DATE-TIME") from e
        elif value == "DATE-TIME":
            # TRIGGERs with DATE-TIME values must be in UTC, we could validate that fact, for now we take it on faith.
            return DateTimeBehavior.transform_to_native(obj)
        else:
            raise ParseError("VALUE must be DURATION or DATE-TIME")

    @staticmethod
    def transform_from_native(obj):
        if type(obj.value) is dt.datetime:
            obj.value_param = "DATE-TIME"
            return UTCDateTimeBehavior.transform_from_native(obj)
        if type(obj.value) is dt.timedelta:
            return Duration.transform_from_native(obj)

        raise NativeError("Native TRIGGER values must be timedelta or datetime")


register_behavior(Trigger)


class PeriodBehavior(Behavior):
    """A list of (date-time, timedelta) tuples."""

    has_native = True

    @staticmethod
    def transform_to_native(obj):
        """
        Convert comma separated periods into tuples.
        """
        if obj.is_native:
            return obj
        obj.is_native = True
        if obj.value == "":
            obj.value = []
            return obj
        tzinfo = get_tzid(getattr(obj, "tzid_param", None))
        obj.value = [string_to_period(x, tzinfo) for x in obj.value.split(",")]
        return obj

    @classmethod
    def transform_from_native(cls, obj):
        """
        Convert the list of tuples in obj.value to strings.
        """
        if obj.is_native:
            obj.is_native = False
            transformed = [period_to_string(tup, cls.force_utc) for tup in obj.value]
            if transformed:
                tzid = TimezoneComponent.register_tzinfo(obj.value[-1][0].tzinfo)
                if not cls.force_utc and tzid is not None:
                    obj.tzid_param = tzid

            obj.value = ",".join(transformed)

        return obj


class FreeBusy(PeriodBehavior):
    """
    Free or busy period of time, must be specified in UTC.
    """

    name = "FREEBUSY"
    force_utc = True


register_behavior(FreeBusy, "FREEBUSY")


class RRule(Behavior):
    """
    Dummy behavior to avoid having RRULEs being treated as text lines
    (and thus having semi-colons inaccurately escaped).
    """


register_behavior(RRule, "RRULE")
register_behavior(RRule, "EXRULE")

# ------------------------ Registration of common classes ----------------------
utc_date_time_list = ["LAST-MODIFIED", "CREATED", "COMPLETED", "DTSTAMP"]
list(map(lambda x: register_behavior(UTCDateTimeBehavior, x), utc_date_time_list))

date_time_or_date_list = ["DTEND", "DTSTART", "DUE", "RECURRENCE-ID"]
list(map(lambda x: register_behavior(DateOrDateTimeBehavior, x), date_time_or_date_list))

register_behavior(MultiDateBehavior, "RDATE")
register_behavior(MultiDateBehavior, "EXDATE")

text_list = [
    "CALSCALE",
    "METHOD",
    "PRODID",
    "CLASS",
    "COMMENT",
    "DESCRIPTION",
    "LOCATION",
    "STATUS",
    "SUMMARY",
    "TRANSP",
    "CONTACT",
    "RELATED-TO",
    "UID",
    "ACTION",
    "BUSYTYPE",
]
list(map(lambda x: register_behavior(TextBehavior, x), text_list))

list(map(lambda x: register_behavior(MultiTextBehavior, x), ["CATEGORIES", "RESOURCES"]))
register_behavior(SemicolonMultiTextBehavior, "REQUEST-STATUS")


# ------------------------ Serializing helper functions ------------------------
def timedelta_to_string(delta):
    """
    Convert timedelta to an ical DURATION format: PnYnMnDTnHnMnS
    """
    sign = "-" if delta.days < 0 else ""
    days, hours, minutes, seconds = split_delta(abs(delta))

    output = f"{sign}P"
    if days:
        output += f"{days}D"
    if hours or minutes or seconds:
        output += "T"
    elif not days:  # Deal with zero duration
        output += "T0S"
    if hours:
        output += f"{hours}H"
    if minutes:
        output += f"{minutes}M"
    if seconds:
        output += f"{seconds}S"
    return output


def time_to_string(date_or_date_time):
    """
    Wraps date_to_string and datetime_to_string, returning the results of either based on the type of the argument
    """
    if hasattr(date_or_date_time, "hour"):
        return datetime_to_string(date_or_date_time)
    return date_to_string(date_or_date_time)


def date_to_string(date):
    return date.strftime("%Y%m%d")


def datetime_to_string(date_time, convert_to_utc=False) -> str:
    """
    Ignore tzinfo unless convert_to_utc. Output string.
    """
    if date_time.tzinfo and convert_to_utc:
        date_time = date_time.astimezone(utc)

    datestr = date_time.strftime("%Y%m%dT%H%M%S")
    if tzinfo_eq(date_time.tzinfo, utc):
        datestr += "Z"
    return datestr


def delta_to_offset(delta: dt.timedelta) -> str:
    """Returns offset in format : ±HHMM"""
    # Remark : This code assumes day difference = 0
    abs_delta = split_delta(abs(delta))
    assert abs_delta.days == 0, "rethink this function uses"
    sign_string = "-" if delta.days == -1 else "+"
    return f"{sign_string}{abs_delta.hours:02}{abs_delta.minutes:02}"


def period_to_string(period, convert_to_utc=False):
    txtstart = datetime_to_string(period[0], convert_to_utc)
    if isinstance(period[1], dt.timedelta):
        txtend = timedelta_to_string(period[1])
    else:
        txtend = datetime_to_string(period[1], convert_to_utc)
    return f"{txtstart}/{txtend}"


# ----------------------- Parsing functions ------------------------------------
def is_duration(s):
    return "P" in s[:2].upper()


def string_to_date(s: str) -> dt.date:
    return dt.datetime.strptime(s, "%Y%m%d").date()


def string_to_date_time(s, tzinfo=None, strict=False) -> dt.datetime:
    if not strict:
        s = s.strip()

    try:
        _datetime = dt.datetime.strptime(s[:15], "%Y%m%dT%H%M%S")
        if len(s) > 15 and s[15] == "Z":
            tzinfo = get_tzid("UTC")
    except ValueError as e:
        raise ParseError(f"'{s!s}' is not a valid DATE-TIME") from e
    year = _datetime.year or 2000
    if tzinfo is not None and hasattr(tzinfo, "localize"):  # PyTZ case
        return tzinfo.localize(
            dt.datetime(year, _datetime.month, _datetime.day, _datetime.hour, _datetime.minute, _datetime.second)
        )
    return dt.datetime(
        year, _datetime.month, _datetime.day, _datetime.hour, _datetime.minute, _datetime.second, 0, tzinfo
    )


# DQUOTE included to work around iCal's penchant for backslash escaping it,
# although it isn't actually supposed to be escaped according to rfc2445 TEXT
ESCAPABLE_CHAR_LIST = '\\;,Nn"'


def string_to_text_values(s, list_separator=",", char_list=None):
    """
    Returns list of strings.
    """
    if char_list is None:
        char_list = ESCAPABLE_CHAR_LIST

    def escaped_char(ch: str) -> str:
        if ch not in char_list:
            # leave unrecognized escaped characters for later passes
            return "\\" + ch
        return "\n" if ch in "nN" else ch

    current = []
    results = []
    to_escape = False
    for char in s:
        if to_escape:
            current.append(escaped_char(char))
            to_escape = False
            continue

        if char == "\\":
            to_escape = True
        elif char == list_separator:
            current = "".join(current)
            results.append(current)
            current = []
        else:
            current.append(char)

    if current or not results:
        current = "".join(current)
        results.append(current)
    return results


def parse_dtstart(contentline, allow_signature_mismatch=False):
    """
    Convert a contentline's value into a date or date-time.

    A variety of clients don't serialize dates with the appropriate VALUE parameter, so rather than failing on these
    (technically invalid) lines, if allow_signature_mismatch is True, try to parse both varieties.
    """
    tzinfo = get_tzid(getattr(contentline, "tzid_param", None))
    value_param = getattr(contentline, "value_param", "DATE-TIME").upper()
    parsed_dtstart = None
    if value_param == "DATE":
        parsed_dtstart = string_to_date(contentline.value)
    elif value_param == "DATE-TIME":
        try:
            parsed_dtstart = string_to_date_time(contentline.value, tzinfo)
        except AllException:
            if not allow_signature_mismatch:
                raise
            parsed_dtstart = string_to_date(contentline.value)
    return parsed_dtstart


def string_to_period(s, tzinfo=None):
    values = s.split("/")
    start = string_to_date_time(values[0], tzinfo)
    val_end = values[1]
    if not is_duration(val_end):
        return start, string_to_date_time(val_end, tzinfo)
    # period-start = date-time "/" dur-value
    delta = string_to_durations(val_end)[0]
    return start, delta


def get_transition(transition_to, year, tzinfo):
    """
    Return the datetime of the transition to/from DST, or None.
    """

    def first_transition(iter_dates, test_func):
        """
        Return the last date not matching test, or None if all tests matched.
        """
        success = None
        for _dt in iter_dates:
            if not test_func(_dt):
                success = _dt
            else:
                if success is not None:
                    return success
        return success  # may be None

    def generate_dates(year_, month_=None, day_=None):
        """
        Iterate over possible dates with unspecified values.
        """
        months = range(1, 13)
        days = range(1, 32)
        hours = range(24)
        if month_ is None:
            for _month in months:
                yield dt.datetime(year_, _month, 1)
        elif day_ is None:
            for _day in days:
                with contextlib.suppress(ValueError):
                    yield dt.datetime(year_, month_, _day)
        else:
            for hour in hours:
                yield dt.datetime(year_, month_, day_, hour)

    assert transition_to in _TRANSITIONS

    def test(dt_):
        is_standard_transition = transition_to == "standard"
        is_daylight_transition = not is_standard_transition
        try:
            is_dt_zerodelta = tzinfo.dst(dt_) == zero_delta
            return is_dt_zerodelta if is_standard_transition else not is_dt_zerodelta
        except pytz.NonExistentTimeError:
            return is_daylight_transition  # entering daylight time
        except pytz.AmbiguousTimeError:
            return is_standard_transition  # entering standard time

    month_dt = first_transition(generate_dates(year), test)
    if month_dt is None:
        return dt.datetime(year, 1, 1)  # new year
    if month_dt.month == 12:
        return None

    # there was a good transition somewhere in a non-December month
    month = month_dt.month
    day = first_transition(generate_dates(year, month), test).day
    uncorrected = first_transition(generate_dates(year, month, day), test)
    if transition_to == "standard":
        # assuming tzinfo.dst returns a new offset for the first possible hour, we need to add one hour for the
        # offset change and another hour because first_transition returns the hour before the transition
        return uncorrected + dt.timedelta(hours=2)

    return uncorrected + dt.timedelta(hours=1)


def tzinfo_eq(tzinfo1, tzinfo2, start_year=2000, end_year=2020):
    """
    Compare offsets and DST transitions from start_year to end_year.
    """
    if tzinfo1 == tzinfo2:
        return True
    if tzinfo1 is None or tzinfo2 is None:
        return False

    def dt_test(_dt):
        if _dt is None:
            return True
        return tzinfo1.utcoffset(_dt) == tzinfo2.utcoffset(_dt)

    if not dt_test(dt.datetime(start_year, 1, 1)):
        return False
    for year in range(start_year, end_year):
        for transition_to in _TRANSITIONS:
            t1 = get_transition(transition_to, year, tzinfo1)
            t2 = get_transition(transition_to, year, tzinfo2)
            if t1 != t2 or not dt_test(t1):
                return False
    return True


if __name__ == "__main__":
    print(TimezoneComponent().tzinfo.locals())
