import datetime
import struct
import winreg  # noqa : available in py39-py311
from operator import itemgetter

handle = winreg.ConnectRegistry(None, winreg.HKEY_LOCAL_MACHINE)
tzparent = winreg.OpenKey(handle, "SOFTWARE\\Microsoft\\Windows NT\\CurrentVersion\\Time Zones")
parentsize = winreg.QueryInfoKey(tzparent)[0]

localkey = winreg.OpenKey(handle, "SYSTEM\\CurrentControlSet\\Control\\TimeZoneInformation")
WEEKS = datetime.timedelta(7)


def list_timezones():
    """Return a list of all time zones known to the system."""
    return [winreg.EnumKey(tzparent, i) for i in range(parentsize)]


class Win32tz(datetime.tzinfo):
    """tzinfo class based on win32's timezones available in the registry."""

    def __init__(self, name):
        self.data = Win32tzData(name)

    def utcoffset(self, dt):
        minutes = self.data.dstoffset if self._isdst(dt) else self.data.stdoffset
        return datetime.timedelta(minutes=minutes)

    def dst(self, dt):
        minutes = self.data.dstoffset - self.data.stdoffset if self._isdst(dt) else 0
        return datetime.timedelta(minutes=minutes)

    def tzname(self, dt):
        return self.data.dstname if self._isdst(dt) else self.data.stdname

    def _isdst(self, dt):
        dat = self.data
        dston = pick_nth_weekday(dt.year, dat.dstmonth, dat.dstdayofweek, dat.dsthour, dat.dstminute, dat.dstweeknumber)
        dstoff = pick_nth_weekday(
            dt.year, dat.stdmonth, dat.stddayofweek, dat.stdhour, dat.stdminute, dat.stdweeknumber
        )
        if dston < dstoff:
            return dston <= dt.replace(tzinfo=None) < dstoff

        return not (dstoff <= dt.replace(tzinfo=None) < dston)

    def __repr__(self):
        return f"<win32tz - {self.data.display!s}>"


def pick_nth_weekday(year, month, dayofweek, hour, minute, whichweek):
    """dayofweek == 0 means Sunday, whichweek > 4 means last instance"""
    first = datetime.datetime(year=year, month=month, hour=hour, minute=minute, day=1)
    weekdayone = first.replace(day=((dayofweek - first.isoweekday()) % 7 + 1))
    for n in range(whichweek - 1, -1, -1):
        dt = weekdayone + n * WEEKS
        if dt.month == month:
            return dt


class Win32tzData:
    """Read a registry key for a timezone, expose its contents."""

    def __init__(self, path):
        """Load path, or if path is empty, load local time."""
        if path:
            keydict = values_to_dict(winreg.OpenKey(tzparent, path))
            self.display, self.dstname, self.stdname = itemgetter("Display", "Dlt", "Std")(keydict)

            # see http://ww_winreg.jsiinc.com/SUBA/tip0300/rh0398.htm
            std_tup = dst_tup = struct.unpack("=3l16h", keydict["TZI"])
            self.stdoffset = -std_tup[0] - std_tup[1]  # Bias + StandardBias * -1
            self.dstoffset = self.stdoffset - std_tup[2]  # + DaylightBias * -1

            std_offset = 3
            dst_offset = 11

        else:
            keydict = values_to_dict(localkey)

            self.stdname, self.dstname = itemgetter("StandardName", "DaylightName")(keydict)

            sourcekey = winreg.OpenKey(tzparent, self.stdname)
            self.display = values_to_dict(sourcekey)["Display"]

            self.stdoffset = -keydict["Bias"] - keydict["StandardBias"]
            self.dstoffset = self.stdoffset - keydict["DaylightBias"]

            # see http://wwwinreg.jsiinc.com/SUBA/tip0300/rh0398.htm
            std_tup = struct.unpack("=8h", keydict["StandardStart"])
            dst_tup = struct.unpack("=8h", keydict["DaylightStart"])
            std_offset = dst_offset = 0

        # Sunday=0th day of week # Last week number = 5
        self.stdmonth, self.stddayofweek, self.stdweeknumber, self.stdhour, self.stdminute = next_5(std_tup, std_offset)
        self.dstmonth, self.dstdayofweek, self.dstweeknumber, self.dsthour, self.dstminute = next_5(dst_tup, dst_offset)


def next_5(items, offset=0):
    """Returns next 5 item after 'offset'."""
    return items[offset + 1 : offset + 6]


def values_to_dict(key):
    """Convert a registry key's values to a dictionary."""
    size = winreg.QueryInfoKey(key)[1]
    return {winreg.EnumValue(key, i)[0]: winreg.EnumValue(key, i)[1] for i in range(size)}


def _test():
    import doctest

    import win32tz  # pylint: disable=import-error

    doctest.testmod(win32tz, verbose=False)


if __name__ == "__main__":
    _test()
