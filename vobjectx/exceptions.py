import warnings


class VObjectError(Exception):
    def __init__(self, msg, line_number=None):
        self.msg = msg
        self.line_number = line_number

    def __str__(self):
        if self.line_number is None:
            return repr(self.msg)
        return f"At line {self.line_number!s}: {self.msg!s}"


class ParseError(VObjectError):
    def __init__(self, msg, line_number=None, *, inputs=None):
        super().__init__(msg, line_number)
        self.inputs = inputs


class ValidateError(VObjectError):
    pass


class NativeError(VObjectError):
    pass


class AllException(VObjectError):
    pass


class UnusedBranchError(VObjectError):
    def __init__(self):
        super().__init__("Unexpected Execution : Report a bug", None)


def warn_if_true(cond: bool = True, raise_error: bool = True):
    """Warns if unexpected code excecuttion is encountered."""
    if not cond:
        return

    warnings.warn("Unexpected code execution", UserWarning, stacklevel=2)
    if raise_error:
        raise UnusedBranchError()
