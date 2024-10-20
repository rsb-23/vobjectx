import unittest

from vobject.base import read_components

from .common import get_test_file


class TestCompatibility(unittest.TestCase):

    def _test_radicale_with_quoted_printable(self, ics_file_name: str):
        ics_str = get_test_file(ics_file_name)
        vobjs = read_components(ics_str, allow_qp=True)
        for vo in vobjs:
            self.assertIsNotNone(vo)

    def test_radicale_0816(self):
        self._test_radicale_with_quoted_printable("radicale-0816.ics")

    def test_radicale_0827(self):
        self._test_radicale_with_quoted_printable("radicale-0827.ics")

    def test_radicale_1238_0(self):
        self._test_radicale_with_quoted_printable("radicale-1238-0.ics")

    def test_radicale_1238_1(self):
        self._test_radicale_with_quoted_printable("radicale-1238-1.ics")

    def test_radicale_1238_2(self):
        self._test_radicale_with_quoted_printable("radicale-1238-2.ics")

    def test_radicale_1238_3(self):
        self._test_radicale_with_quoted_printable("radicale-1238-3.ics")

    def test_radicale_1587(self):
        vcf_str = get_test_file("radicale-1587.vcf")
        vobjs = read_components(vcf_str)
        for vo in vobjs:
            self.assertIsNotNone(vo)
            lines = vo.serialize().split("\r\n")
            for line in lines:
                if line.startswith("GEO"):
                    self.assertEqual(line, "GEO:37.386013;-122.082932")
