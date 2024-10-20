import datetime as dt
import sys
from unittest import TestCase, skip, skipUnless

if sys.platform == "win32":
    from vobject.win32tz import Win32tz


@skipUnless(sys.platform == "win32", "This is windows specific module")
class TestWin32tz(TestCase):
    def setUp(self):
        self.local = Win32tz("Central Standard Time")
        self.oct1 = dt.datetime(month=10, year=2004, day=1, tzinfo=self.local)
        self.dec1 = dt.datetime(month=12, year=2004, day=1, tzinfo=self.local)
        self.braz = Win32tz("E. South America Standard Time")

    # TODO: test case taken from doctest, need help.
    @skip("It fails, need debugging")
    def test_dst_braz(self):
        self.assertEqual(self.braz.dst(self.oct1), dt.timedelta(0))
        self.assertEqual(self.braz.dst(self.dec1), dt.timedelta(seconds=3600))

    def test_dst_local(self):
        self.assertEqual(self.oct1.dst(), dt.timedelta(seconds=3600))
        self.assertEqual(self.dec1.dst(), dt.timedelta(0))
