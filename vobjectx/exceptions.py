import warnings


class VObjectError(Exception):
    def __init__(self, msg, line_number=None):
        super().__init__(msg)
        self.line_number = line_number
        self.__notes__ = []

    def add_note(self, note):
        # TODO: remove this for 3.10 deprecation
        self.__notes__.append(note)

    def __str__(self):
        msg = self.args[0]
        if self.line_number is not None:
            msg = f"At line {self.line_number}: {msg}"
        if self.__notes__:
            msg += "\n" + "\n".join(self.__notes__)
        return msg


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
        super().__init__("Unused Branch Error", None)
        super().add_note("Unexpected Execution : Report a bug")


def warn_if_true(cond: bool = True, raise_error: bool = True):
    """Warns if unexpected code excecuttion is encountered."""
    if not cond:
        return

    warnings.warn("Unexpected code execution", UserWarning, stacklevel=2)
    if raise_error:
        raise UnusedBranchError()
