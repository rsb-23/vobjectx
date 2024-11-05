from __future__ import annotations

import logging
from io import StringIO

# ------------------------------------ Logging ---------------------------------
logger = logging.getLogger(__name__)
if not logging.getLogger().handlers:
    handler = logging.StreamHandler()
    formatter = logging.Formatter("%(filename)s:%(lineno)d %(levelname)s %(message)s")
    handler.setFormatter(formatter)
    logger.addHandler(handler)
logger.setLevel(logging.INFO)  # modify log levels here


def get_buffer(x: str | StringIO = None) -> StringIO:
    return StringIO(x) if isinstance(x, str) or x is None else x
