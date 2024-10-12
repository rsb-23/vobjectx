class VObjectError(Exception):
    def __init__(self, msg, line_number=None):
        self.msg = msg
        if line_number is not None:
            self.line_number = line_number

    def __str__(self):
        if hasattr(self, "lineNumber"):
            return f"At line {self.line_number!s}: {self.msg!s}"
        else:
            return repr(self.msg)


class ParseError(VObjectError):
    pass


class ValidateError(VObjectError):
    pass


class NativeError(VObjectError):
    pass


class AllException(VObjectError):
    pass
