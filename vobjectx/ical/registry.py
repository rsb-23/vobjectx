from typing import Any

import pytz

from vobjectx.helper import logger, to_unicode
from vobjectx.helper.constants_tmp import UTC_TZ


class TzidRegistry:
    __tzid_map = {}

    @classmethod
    def register(cls, tzid, tzinfo) -> None:
        """Register a tzid -> tzinfo mapping."""
        cls.__tzid_map[to_unicode(tzid)] = tzinfo

    @classmethod
    def get(cls, tzid, smart: bool = True) -> Any:
        """Return the tzid if it exists, or None."""
        _tz = cls.__tzid_map.get(to_unicode(tzid))
        if smart and tzid and not _tz:
            try:
                _tz = pytz.timezone(tzid)
                cls.register(to_unicode(tzid), _tz)
            except pytz.UnknownTimeZoneError as e:
                logger.error(e)
        return _tz


TzidRegistry.register("UTC", UTC_TZ)


# TODO: Remove class method alias by v1
def register_tzid(tzid, tzinfo):
    TzidRegistry.register(tzid, tzinfo)


def get_tzid(tzid, smart=True):
    TzidRegistry.register(tzid, smart)
