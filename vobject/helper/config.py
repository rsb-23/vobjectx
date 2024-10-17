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


def get_buffer(x=None):
    return StringIO(x)
