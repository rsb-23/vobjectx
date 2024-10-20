"""Translate an ics file's events to a different timezone."""

from argparse import ArgumentParser
from datetime import datetime

import pytz
from dateutil import tz

import vobject as vo


def change_tz(cal, new_timezone, default, utc_only=False, utc_tz=vo.icalendar.utc):
    """
    Change the timezone of the specified component.

    Args:
        cal (Component): the component to change
        new_timezone (tzinfo): the timezone to change to
        default (tzinfo): a timezone to assume if the dtstart or dtend in cal doesn't have an existing timezone
        utc_only (bool): only convert dates that are in utc
        utc_tz (tzinfo): the tzinfo to compare to for UTC when processing utc_only=True
    """

    for vevent in getattr(cal, "vevent_list", []):
        start = getattr(vevent, "dtstart", None)
        end = getattr(vevent, "dtend", None)
        for node in (start, end):
            if node:
                dt = node.value
                if isinstance(dt, datetime) and (not utc_only or dt.tzinfo == utc_tz):
                    if dt.tzinfo is None:
                        dt = dt.replace(tzinfo=default)
                    node.value = dt.astimezone(new_timezone)


def show_timezones():
    for tz_string in pytz.all_timezones:
        print(tz_string)


def convert_events(utc_only, args):
    print(f'Converting {"only UTC" if utc_only else "all"} events')
    ics_file = args[0]
    _tzone = args[1] if len(args) > 1 else "UTC"

    print(f"... Reading {ics_file}")
    cal = vo.read_one(open(ics_file))
    change_tz(cal, new_timezone=tz.gettz(_tzone), default=tz.gettz("UTC"), utc_only=utc_only)

    out_name = f"{ics_file}.converted"
    print(f"... Writing {out_name}")
    with open(out_name, "wb") as out:
        cal.serialize(out)

    print("Done")


def main():
    options, args = get_options()

    if options.list:
        show_timezones()
    elif args:
        convert_events(utc_only=options.utc, args=args)


def get_options():
    # Configuration options
    usage = """usage: %prog [options] ics_file [timezone]"""
    parser = ArgumentParser(usage=usage, description="change_tz will convert the timezones in an ics file. ")
    parser.add_argument("--version", action="version", version=vo.VERSION)

    parser.add_argument(
        "-u", "--only-utc", dest="utc", action="store_true", default=False, help="Only change UTC events."
    )
    parser.add_argument(
        "-l", "--list", dest="list", action="store_true", default=False, help="List available timezones"
    )

    (cmdline_options, args) = parser.parse_args()
    if not (args or cmdline_options.list):
        print("error: too few arguments given")
        print(parser.format_help())
        return cmdline_options, False

    return cmdline_options, args


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("Aborted")
