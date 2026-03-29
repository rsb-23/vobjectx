import datetime as dt
import sys

import pytest

if sys.platform == "win32":
    from vobjectx.win32tz import Win32tz


@pytest.mark.skipif(sys.platform != "win32", reason="This is a windows-specific module")
class TestWin32tz:
    @pytest.fixture(autouse=True)
    def setup(self):
        # pylint:disable=E0606,W0201
        _north_tz = Win32tz("Central Standard Time")
        self.oct_2004 = dt.datetime(month=10, year=2004, day=1, tzinfo=_north_tz)
        self.dec_2004 = dt.datetime(month=12, year=2004, day=1, tzinfo=_north_tz)

    def test_no_dst(self):
        no_dst_tz = Win32tz("India Standard Time")
        assert no_dst_tz.dst(self.oct_2004) == dt.timedelta(0)
        assert no_dst_tz.dst(self.dec_2004) == dt.timedelta(0)

    def test_northern_dst(self):
        # October = DST active, December = standard time
        assert self.oct_2004.dst() == dt.timedelta(seconds=3600)
        assert self.dec_2004.dst() == dt.timedelta(0)

    def test_southern_dst(self):
        # October = standard time, December = DST active
        south_tz = Win32tz("AUS Eastern Standard Time")
        assert south_tz.dst(self.oct_2004) == dt.timedelta(0)
        assert south_tz.dst(self.dec_2004) == dt.timedelta(seconds=3600)

    @pytest.mark.skip(reason="Requires historical DST support")
    def test_changed_dst(self):
        # Brazil observed DST in 2004 but abolished it in 2019
        braz_tz = Win32tz("E. South America Standard Time")
        # 2004: Brazil had DST (Southern Hemisphere: Oct=standard, Dec=DST)
        assert braz_tz.dst(self.oct_2004) == dt.timedelta(0)
        assert braz_tz.dst(self.dec_2004) == dt.timedelta(seconds=3600)

        # 2021: Brazil no longer has DST (abolished in 2019)
        oct_2021 = dt.datetime(month=10, year=2021, day=1, tzinfo=braz_tz)
        dec_2021 = dt.datetime(month=12, year=2021, day=1, tzinfo=braz_tz)
        assert braz_tz.dst(oct_2021) == dt.timedelta(0)
        assert braz_tz.dst(dec_2021) == dt.timedelta(0)
