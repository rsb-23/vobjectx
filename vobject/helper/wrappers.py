import re
import warnings
from functools import wraps

from vobject.helper.config import logger


def deprecated(func=None):
    """This is a decorator which can be used to mark functions as deprecated.
    It will result in a warning being emitted when the function is used."""

    def camel_to_snake(name):
        s1 = re.sub("(.)([A-Z][a-z]+)", r"\1_\2", name)
        x = re.sub("([a-z0-9])([A-Z])", r"\1_\2", s1).lower()
        return x.replace("date_time", "datetime")

    @wraps(func)
    def wrapper(*args, **kwargs):
        func_name = func.__name__
        warnings.simplefilter("always", DeprecationWarning)  # turn off filter
        new_func = camel_to_snake(func_name)
        warnings.warn(
            f"{func_name}() is deprecated, use {new_func}() instead", category=DeprecationWarning, stacklevel=2
        )
        warnings.simplefilter("default", DeprecationWarning)  # reset filter
        return func(*args, **kwargs)

    return wrapper


def grab_testcase(func):
    """This is a decorator logs inputs and outputs of a func"""

    @wraps(func)
    def wrapper(*args, **kwargs):
        logger.warning(func.__name__)
        logger.warning(f"{args=}, {kwargs}")
        result = func(*args, **kwargs)
        logger.warning(f"{result=}")
        return result

    return wrapper
