"""TZID registry for iCalendar timezone handling.

This module provides a registry for mapping timezone identifiers (TZIDs)
to tzinfo objects, with automatic fallback to zoneinfo for unknown timezones.
"""

import zoneinfo

from vobjectx.helper import logger
from vobjectx.helper.constants_tmp import UTC_TZ
from vobjectx.helper.imports_ import Any


def to_unicode(value: str | bytes):
    """Converts a string argument to a unicode string.

    If the argument is already a unicode string, it is returned
    unchanged.  Otherwise it must be a byte string and is decoded as utf8.
    """
    return value.decode() if isinstance(value, bytes) else value


class TzidRegistry:
    __tzid_map = {}

    @classmethod
    def get(cls, tzid, *, smart: bool = True) -> Any:
        """Return the tzid if it exists, or None."""
        _tz = cls.__tzid_map.get(to_unicode(tzid))
        if smart and tzid and not _tz:
            try:
                _tz = zoneinfo.ZoneInfo(tzid)
                cls.register(tzid, _tz)  # caches zoneinfo timezone
            except zoneinfo.ZoneInfoNotFoundError as e:
                logger.error(f"Unknown timezone: {tzid} - {e}")
        return _tz

    @classmethod
    def register(cls, tzid, tzinfo) -> None:
        """Register a tzid to tzinfo mapping."""
        cls.__tzid_map[to_unicode(tzid)] = tzinfo

    @classmethod
    def unregister(cls, tzid) -> None:
        """Unregister a tzid from tzinfo mapping."""
        cls.__tzid_map.pop(to_unicode(tzid), None)

    @classmethod
    def reset(cls) -> None:
        """Resets tzinfo mapping to initial state."""
        cls.__tzid_map.clear()
        cls.register("UTC", UTC_TZ)


TzidRegistry.register("UTC", UTC_TZ)
