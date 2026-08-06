import datetime as dt

from dateutil import tz

TEST_FILE_DIR = "tests/test_files"

two_hours = dt.timedelta(hours=2)
UTC_TZ = tz.tzutc()


def get_test_file(file_name: str) -> str:
    """Helper function to open and read test files."""
    filepath = f"{TEST_FILE_DIR}/{file_name}"
    with open(filepath, encoding="utf-8") as f:
        text = f.read()
    return text


# Minimal ICS wrapper so we can feed RDATE lines through the full parse stack.
_VCAL_TMPL = """\
BEGIN:VCALENDAR\r\n\
VERSION:2.0\r\n\
PRODID:-//Test//Test//EN\r\n\
BEGIN:VEVENT\r\n\
UID:{uid}\r\n\
DTSTART:19960403T020000Z\r\n\
DTSTAMP:20240101T000000Z\r\n\
{extra}\r\n\
END:VEVENT\r\n\
END:VCALENDAR\r\n\
"""


def _make_cal(extra_line: str, uid: str = "test@example.com") -> str:
    return _VCAL_TMPL.format(uid=uid, extra=extra_line)
