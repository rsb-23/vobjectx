import socket

from dateutil import rrule, tz

DATENAMES = ("rdate", "exdate")
RULENAMES = ("exrule", "rrule")
DATES_AND_RULES = (*RULENAMES, *DATENAMES)

WEEKDAYS = tuple(str(x) for x in rrule.weekdays)

TRANSITIONS = "daylight", "standard"

UTC_TZ = tz.tzutc()


HOSTNAME = socket.gethostname()
