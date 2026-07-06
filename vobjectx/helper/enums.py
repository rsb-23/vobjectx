import sys

if sys.version_info >= (3, 11):
    from enum import StrEnum
else:
    from enum import Enum

    class StrEnum(str, Enum):
        def __str__(self):
            return str(self.value)


class Param(StrEnum):
    DATE = "DATE"
    DATETIME = "DATE-TIME"
    DESCRIPTION = "DESCRIPTION"
    DTEND = "DTEND"
    DTSTART = "DTSTART"
    DURATION = "DURATION"
    LOCATION = "LOCATION"
    PERIOD = "PERIOD"
    SUMMARY = "SUMMARY"
    TIME = "TIME"
    URL = "URL"


P = Param
