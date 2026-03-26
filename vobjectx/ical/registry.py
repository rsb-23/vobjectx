"""TZID registry for iCalendar timezone handling.

This module provides a registry for mapping timezone identifiers (TZIDs)
to tzinfo objects, with automatic fallback to pytz for unknown timezones.
"""

from typing import Any

import pytz

from vobjectx.helper import logger, to_unicode
from vobjectx.helper.constants_tmp import UTC_TZ


class TzidRegistry:
    __tzid_map = {}

    @classmethod
    def get(cls, tzid, *, smart: bool = True) -> Any:
        """Return the tzid if it exists, or None."""
        _tz = cls.__tzid_map.get(to_unicode(tzid))
        if smart and tzid and not _tz:
            try:
                _tz = pytz.timezone(tzid)
                cls.register(tzid, _tz)  # caches pytz timezone
            except pytz.UnknownTimeZoneError as e:
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
