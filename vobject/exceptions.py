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
