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

from datetime import date, timedelta

from .base import register_behavior
from .helper import Character, get_buffer, pretty_xml
from .icalendar import VCalendar2_0


class Event:
    def __init__(self, event):
        self.url = event.get_child_value("url")
        self.summary = event.get_child_value("summary")
        self.dtstart = event.get_child_value("dtstart")
        self.dtend = event.get_child_value("dtend")
        self.location = event.get_child_value("location")
        self.duration = event.get_child_value("duration")
        self.description = event.get_child_value("description")

    @staticmethod
    def machine_date(date_obj):
        return date_obj.strftime("%Y%m%d" if type(date_obj) is date else "%Y%m%dT%H%M%S%z")

    @staticmethod
    def human_date(date_obj):
        return date_obj.strftime("%A, %B %e" if type(date_obj) is date else "%A, %B %e, %H:%M")


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
            _event_data = [get_xml("summary", _event.summary, tag="span")]  # SUMMARY

            # DTSTART
            if _event.dtstart:
                # TODO: Handle non-datetime formats? Spec says we should handle when dtstart isn't included

                _event_data.append(
                    f'<abbr class="dtstart", title="{_event.machine_date(_event.dtstart)}"'
                    f">{_event.human_date(_event.dtstart)}</abbr>"
                )

                # DTEND
                if not _event.dtend and _event.duration:
                    _event.dtend = _event.duration + _event.dtstart
                # TODO: If lacking dtend & duration?

                if _event.dtend:
                    human = _event.dtend
                    # TODO: Human readable part could be smarter, excluding repeated data
                    if type(_event.dtend) is date:
                        human = _event.dtend - timedelta(days=1)

                    _event_data.append(
                        f'- <abbr class="dtend", title="{_event.machine_date(_event.dtend)}"'
                        f">{_event.human_date(human)}</abbr>"
                    )

            # LOCATION
            _event_data.append(get_xml("location", _event.location, tag="span", prefix="at "))
            _event_data.append(get_xml("description", _event.description, tag="div"))

            _event_str = Character.CRLF.join(_event_data)
            if _event.url:
                _event_str = f'<a class="url" href="{_event.url}">{_event_str}</a>'
            _event_str = f'<span class="vevent">{_event_str}</span>'

            outbuf.write(pretty_xml(_event_str, indent=cls.indent_width))

        return outbuf.getvalue()


register_behavior(HCalendar)
