# pylint: disable=c0123
r"""
hCalendar: A microformat for serializing iCalendar data
          (http://microformats.org/wiki/hcalendar)

Here is a sample event in an iCalendar:

BEGIN:VCALENDAR
PRODID:-//XYZproduct//EN
VERSION:2.0
BEGIN:VEVENT
URL:http://www.web2con.com/
DTSTART:20051005
DTEND:20051008
SUMMARY:Web 2.0 Conference
LOCATION:Argent Hotel\, San Francisco\, CA
END:VEVENT
END:VCALENDAR

and an equivalent event in hCalendar format with various elements optimized appropriately.

<span class="vevent">
 <a class="url" href="http://www.web2con.com/">
  <span class="summary">Web 2.0 Conference</span>:
  <abbr class="dtstart" title="2005-10-05">October 5</abbr>-
  <abbr class="dtend" title="2005-10-08">7</abbr>,
 at the <span class="location">Argent Hotel, San Francisco, CA</span>
 </a>
</span>
"""

import datetime as dt

from .helper import Character, P, get_buffer, logger, pretty_xml
from .icalendar import VCalendar2_0
from .registry import BehaviorRegistry


class Event:
    def __init__(self, event):
        self.url = event.get_child_value(P.URL)
        self.summary = event.get_child_value(P.SUMMARY)
        self.dtstart = event.get_child_value(P.DTSTART)
        self.dtend = event.get_child_value(P.DTEND)
        self.location = event.get_child_value(P.LOCATION)
        self.duration = event.get_child_value(P.DURATION)
        self.description = event.get_child_value(P.DESCRIPTION)

    @staticmethod
    def machine_date(date_obj) -> str:
        return date_obj.strftime("%Y%m%d" if type(date_obj) is dt.date else "%Y%m%dT%H%M%S%z")

    @staticmethod
    def human_date(human, start=None) -> str:
        """
        Return a shortened end-date label by omitting context already given by *start*.

        For date objects (all-day events, where human = dtend - 1 day):
            same year and month  → day number only,        e.g. "7"
            same year, diff month → month + day,           e.g. "November  2"
            different year        → full human_date string

        For datetime objects (timed events, where human = dtend as-is):
            same calendar day    → time only,              e.g. "17:00"
            same year and month  → day + time,             e.g. "7, 09:00"
            otherwise            → full human_date string
        """
        if start is None:
            return human.strftime("%A, %B %e" if type(human) is dt.date else "%A, %B %e, %H:%M")

        if type(human) is dt.date:
            if human.year == start.year:
                if human.month == start.month:
                    return str(human.day)
                return human.strftime("%B %e")
        else:
            start_date = start.date() if isinstance(start, dt.datetime) else start
            if human.date() == start_date:
                return human.strftime("%H:%M")
            if human.year == start.year and human.month == start.month:
                return f"{human.day}, {human.strftime('%H:%M')}"

        return human.strftime("%A, %B %e" if type(human) is dt.date else "%A, %B %e, %H:%M")


class HCalendar(VCalendar2_0):
    name = "HCALENDAR"
    indent_width = 3

    @classmethod
    def serialize(cls, obj, buf=None, line_length=None, validate=True, *args, **kwargs):
        """
        Serialize iCalendar to HTML using the hCalendar microformat (http://microformats.org/wiki/hcalendar)
        """

        outbuf = buf or get_buffer()

        def get_xml(event_child: str, value, *, tag="span", prefix="") -> str:
            if value:
                return f'{prefix}<{tag} class="{event_child}">{value}</{tag}>:'
            return ""

        # not serializing optional vcalendar wrapper

        vevents = obj.vevent_list

        for event in vevents:
            _event = Event(event)
            _event_data = [get_xml(P.SUMMARY, _event.summary, tag="span")]  # SUMMARY

            # DTSTART
            if _event.dtstart is None:
                logger.warning("hCalendar event missing DTSTART; omitting date output")
            else:
                _event_data.append(
                    f'<abbr class="dtstart", title="{_event.machine_date(_event.dtstart)}"'
                    f">{_event.human_date(_event.dtstart)}</abbr>"
                )

                # DTEND
                if not _event.dtend:
                    if _event.duration:
                        _event.dtend = _event.dtstart + _event.duration
                    else:
                        logger.warning("hCalendar event has no DTEND or DURATION; omitting end date")

                if _event.dtend:
                    human = _event.dtend
                    # TODO: Human readable part could be smarter, excluding repeated data
                    if type(_event.dtend) is dt.date:
                        human = _event.dtend - dt.timedelta(days=1)

                    _event_data.append(
                        f'- <abbr class="dtend", title="{_event.machine_date(_event.dtend)}"'
                        f">{_event.human_date(human)}</abbr>"
                    )

            # LOCATION
            _event_data.append(get_xml(P.LOCATION, _event.location, tag="span", prefix="at "))
            _event_data.append(get_xml(P.DESCRIPTION, _event.description, tag="div"))

            _event_str = Character.CRLF.join(_event_data)
            if _event.url:
                _event_str = f'<a class="url" href="{_event.url}">{_event_str}</a>'
            _event_str = f'<span class="vevent">{_event_str}</span>'

            outbuf.write(pretty_xml(_event_str, indent=cls.indent_width))

        return outbuf.getvalue()


BehaviorRegistry.register(HCalendar)
