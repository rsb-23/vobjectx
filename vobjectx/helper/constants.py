from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Character:
    """Space and Line-break characters"""

    CR = "\r"
    LF = "\n"
    CRLF = CR + LF
    SPACE = " "
    TAB = "\t"
    SPACEORTAB = SPACE + TAB
