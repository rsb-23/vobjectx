from dateutil import rrule, tz

# ------------------------------- Constants ------------------------------------
DATENAMES = ("rdate", "exdate")
RULENAMES = ("exrule", "rrule")
DATESANDRULES = ("exrule", "rrule", "rdate", "exdate")

WEEKDAYS = [str(x) for x in rrule.weekdays]

TRANSITIONS = "daylight", "standard"

UTC_TZ = tz.tzutc()
