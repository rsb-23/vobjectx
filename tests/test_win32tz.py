import datetime as dt
import sys

import pytest

if sys.platform == "win32":
    from vobjectx.win32tz import Win32tz


@pytest.mark.skipif(sys.platform != "win32", reason="This is a windows-specific module")
class TestWin32tz:
    @pytest.fixture(autouse=True)
    def setup(self):
        # pylint:disable=E0601,E0606,W0201
        self.local = Win32tz("Central Standard Time")
        self.oct1 = dt.datetime(month=10, year=2004, day=1, tzinfo=self.local)
        self.dec1 = dt.datetime(month=12, year=2004, day=1, tzinfo=self.local)
        self.braz = Win32tz("E. South America Standard Time")

    # TODO: test case taken from doctest, need help.
    @pytest.mark.skip(reason="This test fails and needs debugging")
    def test_dst_braz(self):
        assert self.braz.dst(self.oct1) == dt.timedelta(0)
        assert self.braz.dst(self.dec1) == dt.timedelta(seconds=3600)

    def test_dst_local(self):
        assert self.oct1.dst() == dt.timedelta(seconds=3600)
        assert self.dec1.dst() == dt.timedelta(0)
