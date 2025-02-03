import pytest

from vobject.base import read_components

from .common import get_test_file


@pytest.mark.parametrize(
    "ics_file_name",
    [
        "radicale-0816.ics",
        "radicale-0827.ics",
        "radicale-1238-0.ics",
        "radicale-1238-1.ics",
        "radicale-1238-2.ics",
        "radicale-1238-3.ics",
    ],
)
def test_radicale_with_quoted_printable(ics_file_name: str):
    """Parameterized test for quoted-printable files."""
    ics_str = get_test_file(ics_file_name)
    vobjs = read_components(ics_str, allow_qp=True)
    for vo in vobjs:
        assert vo is not None


def test_radicale_1587():
    vcf_str = get_test_file("radicale-1587.vcf")
    vobjs = read_components(vcf_str)
    for vo in vobjs:
        assert vo is not None
        lines = vo.serialize().split("\r\n")
        for line in lines:
            if line.startswith("GEO"):
                assert line == "GEO:37.386013;-122.082932"
