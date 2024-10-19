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

from datetime import date, datetime, timedelta

from .base import register_behavior
from .helper import Character, get_buffer, indent_str
from .icalendar import VCalendar2_0


class HCalendar(VCalendar2_0):
    name = "HCALENDAR"

    @classmethod
    def serialize(cls, obj, buf=None, line_length=None, validate=True, *args, **kwargs):
        """
        Serialize iCalendar to HTML using the hCalendar microformat (http://microformats.org/wiki/hcalendar)
        """

        outbuf = buf or get_buffer()
        level, tabwidth = 0, 3  # holds current indentation level

        def buffer_write(s):
            outbuf.write(f"{indent_str(level=level, tabwidth=tabwidth)}{s}{Character.CRLF}")

        # not serializing optional vcalendar wrapper

        vevents = obj.vevent_list

        for event in vevents:
            buffer_write('<span class="vevent">')
            level += 1

            # URL
            url = event.get_child_value("url")
            if url:
                buffer_write(f'<a class="url" href="{url}">')
                level += 1
            # SUMMARY
            summary = event.get_child_value("summary")
            if summary:
                buffer_write(f'<span class="summary">{summary}</span>:')

            # DTSTART
            dtstart = event.get_child_value("dtstart")
            if dtstart:
                machine = timeformat = ""
                if type(dtstart) is date:
                    timeformat = "%A, %B %e"
                    machine = "%Y%m%d"
                elif type(dtstart) is datetime:
                    timeformat = "%A, %B %e, %H:%M"
                    machine = "%Y%m%dT%H%M%S%z"

                # TODO: Handle non-datetime formats?
                # TODO: Spec says we should handle when dtstart isn't included

                buffer_write(
                    f'<abbr class="dtstart", title="{dtstart.strftime(machine)}">{dtstart.strftime(timeformat)}</abbr>'
                )

                # DTEND
                dtend = event.get_child_value("dtend")
                if not dtend:
                    duration = event.get_child_value("duration")
                    if duration:
                        dtend = duration + dtstart
                # TODO: If lacking dtend & duration?

                if dtend:
                    human = dtend
                    # TODO: Human readable part could be smarter, excluding repeated data
                    if type(dtend) is date:
                        human = dtend - timedelta(days=1)

                    buffer_write(
                        f'- <abbr class="dtend", title="{dtend.strftime(machine)}">{human.strftime(timeformat)}</abbr>'
                    )

            # LOCATION
            location = event.get_child_value("location")
            if location:
                buffer_write(f'at <span class="location">{location}</span>')

            description = event.get_child_value("description")
            if description:
                buffer_write(f'<div class="description">{description}</div>')

            if url:
                level -= 1
                buffer_write("</a>")

            level -= 1
            buffer_write("</span>")  # close vevent

        return buf or outbuf.getvalue()


register_behavior(HCalendar)
