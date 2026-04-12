import datetime as dt
import zoneinfo
from typing import Protocol

from vobjectx.helper import logger
from vobjectx.helper.constants_tmp import UTC_TZ


def to_unicode(value: str | bytes):
    """Converts a string argument to a unicode string.

    If the argument is already a unicode string, it is returned
    unchanged.  Otherwise it must be a byte string and is decoded as utf8.
    """
    return value.decode() if isinstance(value, bytes) else value


class BehaviorProtocol(Protocol):
    name: str
    version_string: str
    is_component: bool

    @classmethod
    def decode(cls, line):
        pass

    @classmethod
    def encode(cls, line):
        pass


class BehaviorRegistry:
    __registry = {}

    @classmethod
    def keys(cls) -> list[str]:
        return list(cls.__registry.keys())

    @classmethod
    def get(cls, name: str, id_=None) -> BehaviorProtocol | None:
        """
        Return a matching behavior if it exists, or None.

        If id is None, return the default for name.
        """
        name = name.upper()
        if name in cls.__registry:
            named_registry = cls.__registry[name]
            return named_registry.get(id_) or named_registry["default_"]
        return None

    @classmethod
    def register(cls, behavior: BehaviorProtocol, name=None, default=False, id_=None):
        """
        Register the given behavior.

        If default is True (or if this is the first version registered with this
        name), the version will be the default if no id is given.
        """
        if not name:
            name = behavior.name.upper()
        if id_ is None:
            id_ = behavior.version_string
        if name in cls.__registry:
            cls.__registry[name][id_] = behavior
            if default:
                cls.__registry[name]["default_"] = behavior
        else:
            cls.__registry[name] = {id_: behavior, "default_": behavior}


class TzidRegistry:
    """TZID registry for iCalendar timezone handling.

    A registry for mapping timezone identifiers (TZIDs) to tzinfo objects,
    with automatic fallback to zoneinfo for unknown timezones.
    """

    __tzid_map: dict[str, dt.tzinfo | None] = {}

    @classmethod
    def get(cls, tzid) -> dt.tzinfo | None:
        """Return the tzid if it exists, or None."""
        return cls.__tzid_map.get(to_unicode(tzid))

    @classmethod
    def register(cls, tzid, tzinfo: dt.tzinfo, *, exist_ok: bool = False) -> None:
        """Register a new tzid to tzinfo mapping."""

        _key = to_unicode(tzid)
        if _key in cls.__tzid_map:
            if exist_ok:
                return
            raise KeyError(f"Tzid {_key} already registered")

        try:
            tzinfo = zoneinfo.ZoneInfo(tzid)
        except zoneinfo.ZoneInfoNotFoundError as e:
            logger.error(f"Unknown timezone: {tzid} - {e}")

        cls.__tzid_map[_key] = tzinfo

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
