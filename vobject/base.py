"""vobject module for reading vCard and vCalendar files."""

from .exceptions import NativeError, ParseError, VObjectError
from .helper import Character as Char
from .helper import byte_decoder, get_buffer, logger, split_by_size
from .helper.imports_ import TextIO, contextlib, copy, lru_cache, re, sys


def to_unicode(value):
    """Converts a string argument to a unicode string.

    If the argument is already a unicode string, it is returned
    unchanged.  Otherwise it must be a byte string and is decoded as utf8.
    """
    return value if isinstance(value, str) else value.decode("utf-8")


def to_basestring(s):
    """Converts a string argument to a byte string.

    If the argument is already a byte string, it is returned unchanged.
    Otherwise it must be a unicode string and is encoded as utf8.
    """
    return s if isinstance(s, bytes) else s.encode("utf-8")


# --------------------------------- Main classes -------------------------------
class ContentDict(dict):
    def __setattr__(self, key, value):
        if type(value) is list:
            if key.endswith("_list"):
                key = key[:-5]
        elif key.endswith("_list"):
            raise VObjectError("Component list set to a non-list")
        else:
            value = [value]
        object.__setattr__(self, to_vname(key), value)

    def __delattr__(self, key):
        if key.endswith("_list"):
            key = key[:-5]
        object.__delattr__(self, to_vname(key))


class VBase:
    """
    Base class for ContentLine and Component.

    @ivar behavior:
        The Behavior class associated with this object, which controls
        validation, transformations, and encoding.
    @ivar parent_behavior:
        The object's parent's behavior, or None if no behaviored parent exists.
    @ivar is_native:
        Boolean describing whether this component is a Native instance.
    @ivar group:
        An optional group prefix, should be used only to indicate sort order in
        vCards, according to spec.

    Current spec: 4.0 (http://tools.ietf.org/html/rfc6350)
    """

    def __init__(self, group=None, *args, **kwds):
        super().__init__(*args, **kwds)
        self.name = None
        self.group = group
        self.behavior = None
        self.parent_behavior = None
        self.is_native = False
        # self.encoded = None  # kwds.get("encoded")

    def copy(self, copyit):
        self.group = copyit.group
        self.behavior = copyit.behavior
        self.parent_behavior = copyit.parent_behavior
        self.is_native = copyit.is_native

    def validate(self, *args, **kwds):
        """
        Call the behavior's validate method, or return True.
        """
        return self.behavior.validate(self, *args, **kwds) if self.behavior else True

    def get_children(self):
        """
        Return an iterable containing the contents of the object.
        """
        return []

    def clear_behavior(self, cascade=True):
        """
        Set behavior to None. Do for all descendants if cascading.
        """
        self.behavior = None
        if cascade:
            self.transform_children_from_native()

    def auto_behavior(self, cascade=False):
        """
        Set behavior if name is in self.parent_behavior.known_children.

        If cascade is True, unset behavior and parent_behavior for all
        descendants, then recalculate behavior and parent_behavior.
        """
        parent_behavior = self.parent_behavior
        if parent_behavior is not None:
            known_child_tup = parent_behavior.known_children.get(self.name)
            if known_child_tup is not None:
                behavior = get_behavior(self.name, known_child_tup[2])
                if behavior is not None:
                    self.set_behavior(behavior, cascade)
                    if isinstance(self, ContentLine) and self.encoded:
                        self.behavior.decode(self)
            elif isinstance(self, ContentLine):
                self.behavior = parent_behavior.default_behavior
                if self.encoded and self.behavior:
                    self.behavior.decode(self)

    def set_behavior(self, behavior, cascade=True):
        """
        Set behavior. If cascade is True, auto_behavior all descendants.
        """
        self.behavior = behavior
        if cascade:
            for obj in self.get_children():
                obj.parent_behavior = behavior
                obj.auto_behavior(True)

    def transform_to_native(self):
        """
        Transform this object into a custom VBase subclass.

        transform_to_native should always return a representation of this object.
        It may do so by modifying self in place then returning self, or by
        creating a new object.
        """
        if self.is_native or not self.behavior or not self.behavior.has_native:
            return self

        self_orig = copy.copy(self)
        try:
            return self.behavior.transform_to_native(self)
        except VObjectError as e:
            # wrap errors in transformation in a ParseError
            line_number = getattr(self, "line_number", None)

            if isinstance(e, ParseError):
                if line_number is not None:
                    e.line_number = line_number
                raise
            else:
                msg = "In transform_to_native, unhandled exception on line {0}: {1}: {2}"
                msg = msg.format(line_number, sys.exc_info()[0], sys.exc_info()[1])
                msg = f"{msg} ({str(self_orig)})"
                raise ParseError(msg, line_number) from e

    def transform_from_native(self):
        """
        Return self transformed into a ContentLine or Component if needed.

        May have side effects.  If it does, transform_from_native and
        transform_to_native MUST have perfectly inverse side effects. Allowing
        such side effects is convenient for objects whose transformations only
        change a few attributes.

        Note that it isn't always possible for transform_from_native to be a
        perfect inverse of transform_to_native, in such cases transform_from_native
        should return a new object, not self after modifications.
        """
        if not self.is_native or not self.behavior or not self.behavior.has_native:
            return self

        try:
            return self.behavior.transform_from_native(self)
        except VObjectError as e:
            # wrap errors in transformation in a NativeError
            line_number = getattr(self, "line_number", None)
            if isinstance(e, NativeError):
                if line_number is not None:
                    e.line_number = line_number
                raise
            else:
                msg = "In transform_from_native, unhandled exception on line {0} {1}: {2}"
                msg = msg.format(line_number, sys.exc_info()[0], sys.exc_info()[1])
                raise NativeError(msg, line_number) from e

    def transform_children_to_native(self):
        """
        Recursively replace children with their native representation.
        """

    def transform_children_from_native(self, clear_behavior=True):
        """
        Recursively transform native children to vanilla representations.
        """

    def serialize(self, buf=None, line_length=75, validate=True, behavior=None, *args, **kwargs):
        """
        Serialize to buf if it exists, otherwise return a string.

        Use self.behavior.serialize if behavior exists.
        """
        if not behavior:
            behavior = self.behavior
        if behavior:
            logger.debug(f"serializing {self.name!s} with behavior {behavior!s}")
            return behavior.serialize(self, buf, line_length, validate, *args, **kwargs)
        else:
            logger.debug(f"serializing {self.name!s} without behavior")
            return default_serialize(self, buf, line_length)


@lru_cache(32)
def to_vname(name, strip_num=0, upper=False):
    """
    Turn a Python name into an iCalendar style name,
    optionally uppercase and with characters stripped off.
    """
    if upper:
        name = name.upper()
    if strip_num != 0:
        name = name[:-strip_num]
    return name.replace("_", "-")


class ContentLine(VBase):
    """
    Holds one content line for formats like vCard and vCalendar.

    For example::
      <SUMMARY{u'param1' : [u'val1'], u'param2' : [u'val2']}Bastille Day Party>

    @ivar name:
        The uppercased name of the contentline.
    @ivar params:
        A dictionary of parameters and associated lists of values (the list may
        be empty for empty parameters).
    @ivar value:
        The value of the contentline.
    @ivar singletonparams:
        A list of parameters for which it's unclear if the string represents the
        parameter name or the parameter value. In vCard 2.1, "The value string
        can be specified alone in those cases where the value is unambiguous".
        This is crazy, but we have to deal with it.
    @ivar encoded:
        A boolean describing whether the data in the content line is encoded.
        Generally, text read from a serialized vCard or vCalendar should be
        considered encoded.  Data added programmatically should not be encoded.
    @ivar line_number:
        An optional line number associated with the contentline.
    """

    def __init__(
        self, name, params, value, group=None, encoded=False, is_native=False, line_number=None, *args, **kwds
    ):
        """
        Take output from parse_line, convert params list to dictionary.

        Group is used as a positional argument to match parse_line's return
        """
        super().__init__(group, *args, **kwds)

        self.name = name.upper()
        self.encoded = encoded
        self.params = {}
        self.singletonparams = []
        self.is_native = is_native
        self.line_number = line_number
        self.value = value

        def update_table(x):
            if len(x) == 1:
                self.singletonparams += x
            else:
                paramlist = self.params.setdefault(x[0].upper(), [])
                paramlist.extend(x[1:])

        list(map(update_table, params))

        qp = False
        if "ENCODING" in self.params and "QUOTED-PRINTABLE" in self.params["ENCODING"]:
            qp = True
            self.params["ENCODING"].remove("QUOTED-PRINTABLE")
            if len(self.params["ENCODING"]) == 0:
                del self.params["ENCODING"]
        if "QUOTED-PRINTABLE" in self.singletonparams:
            qp = True
            self.singletonparams.remove("QUOTED-PRINTABLE")
        if qp:
            if "ENCODING" in self.params:
                _encoding = self.params["ENCODING"]
            elif "CHARSET" in self.params:
                _encoding = self.params["CHARSET"][0]
            else:
                _encoding = "utf-8"
            self.value = byte_decoder(self.value, "quoted-printable").decode(_encoding)

    @classmethod
    def duplicate(cls, copyit):
        newcopy = cls("", {}, "")
        newcopy.copy(copyit)
        return newcopy

    def copy(self, copyit):
        super().copy(copyit)
        self.name = copyit.name
        self.value = copy.copy(copyit.value)
        self.encoded = self.encoded
        self.params = copy.copy(copyit.params)
        for k, v in self.params.items():
            self.params[k] = copy.copy(v)
        self.singletonparams = copy.copy(copyit.singletonparams)
        self.line_number = copyit.line_number

    def __eq__(self, other):
        return (self.name == other.name) and (self.params == other.params) and (self.value == other.value)

    def __getattr__(self, name):
        """
        Make params accessible via self.foo_param or self.foo_paramlist.

        Underscores, legal in python variable names, are converted to dashes,
        which are legal in IANA tokens.
        """
        try:
            if name.endswith("_param"):
                return self.params[to_vname(name, 6, True)][0]
            elif name.endswith("_paramlist"):
                return self.params[to_vname(name, 10, True)]
            else:
                raise AttributeError(name)
        except KeyError as e:
            raise AttributeError(name) from e

    def __setattr__(self, name, value):
        """
        Make params accessible via self.foo_param or self.foo_paramlist.

        Underscores, legal in python variable names, are converted to dashes,
        which are legal in IANA tokens.
        """
        if name.endswith("_param"):
            if type(value) is list:
                self.params[to_vname(name, 6, True)] = value
            else:
                self.params[to_vname(name, 6, True)] = [value]
        elif name.endswith("_paramlist"):
            if type(value) is list:
                self.params[to_vname(name, 10, True)] = value
            else:
                raise VObjectError("Parameter list set to a non-list")
        else:
            prop = getattr(self.__class__, name, None)
            if isinstance(prop, property):
                prop.fset(self, value)
            else:
                object.__setattr__(self, name, value)

    def __delattr__(self, name):
        try:
            if name.endswith("_param"):
                del self.params[to_vname(name, 6, True)]
            elif name.endswith("_paramlist"):
                del self.params[to_vname(name, 10, True)]
            else:
                object.__delattr__(self, name)
        except KeyError as e:
            raise AttributeError(name) from e

    def value_repr(self):
        """
        Transform the representation of the value
        according to the behavior, if any.
        """
        return self.behavior.value_repr(self) if self.behavior else self.value

    def __repr__(self):
        try:
            value_repr = self.value_repr()
        except UnicodeEncodeError:
            value_repr = self.value_repr().encode("utf-8")

        return f"<{self.name}{self.params}{value_repr}>"

    def __unicode__(self):
        return f"<{self.name}{self.params}{self.value_repr()}>"

    def pretty_print(self, level=0, tabwidth=3):
        pre = " " * level * tabwidth
        print(pre, f"{self.name}:", self.value_repr())
        if self.params:
            print(pre, "params for ", f"{self.name}:")
            for k in self.params.keys():
                print(pre + " " * tabwidth, k, self.params[k])


class Component(VBase):
    """
    A complex property that can contain multiple ContentLines.

    For our purposes, a component must start with a BEGIN:xxxx line and end with
    END:xxxx, or have a PROFILE:xxx line if a top-level component.

    @ivar contents:
        A dictionary of lists of Component or ContentLine instances. The keys
        are the lowercased names of child ContentLines or Components.
        Note that BEGIN and END ContentLines are not included in contents.
    @ivar name:
        Uppercase string used to represent this Component, i.e VCARD if the
        serialized object starts with BEGIN:VCARD.
    @ivar use_begin:
        A boolean flag determining whether BEGIN: and END: lines should
        be serialized.
    """

    def __init__(self, name=None, *args, **kwds):
        super().__init__(*args, **kwds)
        self.contents = ContentDict()
        if name:
            self.name = name.upper()
            self.use_begin = True
        else:
            self.name = ""
            self.use_begin = False

        self.auto_behavior()

    @classmethod
    def duplicate(cls, copyit):
        newcopy = cls()
        newcopy.copy(copyit)
        return newcopy

    def copy(self, copyit):
        super().copy(copyit)

        # deep copy of contents
        self.contents = ContentDict()
        for key, lvalue in copyit.contents.items():
            newvalue = []
            for value in lvalue:
                newitem = value.duplicate(value)
                newvalue.append(newitem)
            self.contents[key] = newvalue

        self.name = copyit.name
        self.use_begin = copyit.use_begin

    def set_profile(self, name):
        """
        Assign a PROFILE to this unnamed component.

        Used by vCard, not by vCalendar.
        """
        if self.name or self.use_begin:
            if self.name == name:
                return
            raise VObjectError("This component already has a PROFILE or uses BEGIN.")
        self.name = name.upper()

    def __getattr__(self, name):
        """
        For convenience, make self.contents directly accessible.

        Underscores, legal in python variable names, are converted to dashes,
        which are legal in IANA tokens.
        """
        # if the object is being re-created by pickle, self.contents may not
        # be set, don't get into an infinite loop over the issue
        if name == "contents":
            return object.__getattribute__(self, name)
        try:
            if name.endswith("_list"):
                return self.contents[to_vname(name, 5)]
            else:
                return self.contents[to_vname(name)][0]
        except KeyError as e:
            raise AttributeError(name) from e

    def __setattr__(self, name, value):
        """
        For convenience, make self.contents directly accessible.

        Underscores, legal in python variable names, are converted to dashes,
        which are legal in IANA tokens.
        """
        prop = getattr(self.__class__, name, None)
        if isinstance(prop, property):
            prop.fset(self, value)
        else:
            object.__setattr__(self, name, value)

    def get_child_value(self, child_name, default=None, child_number=0):
        """
        Return a child's value (the first, by default), or None.
        """
        child = self.contents.get(to_vname(child_name))
        return default if child is None else child[child_number].value

    def add(self, obj_or_name, group=None):
        """
        Add obj_or_name to contents, set behavior if it can be inferred.

        If obj_or_name is a string, create an empty component or line based on
        behavior. If no behavior is found for the object, add a ContentLine.

        group is an optional prefix to the name of the object (see RFC 2425).
        """
        if isinstance(obj_or_name, VBase):
            obj = obj_or_name
            if self.behavior:
                obj.parent_behavior = self.behavior
                obj.auto_behavior(True)
        else:
            name = obj_or_name.upper()
            try:
                _id = self.behavior.known_children[name][2]
                behavior = get_behavior(name, _id)
                if behavior.is_component:
                    obj = Component(name)
                else:
                    obj = ContentLine(name, [], "", group)
                obj.parent_behavior = self.behavior
                obj.behavior = behavior
                obj = obj.transform_to_native()
            except (KeyError, AttributeError):
                obj = ContentLine(obj_or_name, [], "", group)
            if obj.behavior is None and self.behavior is not None and isinstance(obj, ContentLine):
                obj.behavior = self.behavior.default_behavior
        self.contents.setdefault(obj.name.lower(), []).append(obj)
        return obj

    def remove(self, obj):
        """
        Remove obj from contents.
        """
        named = self.contents.get(obj.name.lower())
        if named:
            with contextlib.suppress(ValueError):
                named.remove(obj)
                if len(named) == 0:
                    del self.contents[obj.name.lower()]

    def get_children(self):
        """
        Return an iterable of all children.
        """
        for obj_list in self.contents.values():
            yield from obj_list

    def components(self):
        """
        Return an iterable of all Component children.
        """
        return (i for i in self.get_children() if isinstance(i, Component))

    def lines(self):
        """
        Return an iterable of all ContentLine children.
        """
        return (i for i in self.get_children() if isinstance(i, ContentLine))

    def sort_child_keys(self):
        try:
            first = [s for s in self.behavior.sort_first if s in self.contents]
        except AttributeError:
            first = []
        return first + sorted(k for k in self.contents.keys() if k not in first)

    def get_sorted_children(self):
        return [obj for k in self.sort_child_keys() for obj in self.contents[k]]

    def set_behavior_from_version_line(self, version_line):
        """
        Set behavior if one matches name, version_line.value.
        """
        v = get_behavior(self.name, version_line.value)
        if v:
            self.set_behavior(v)

    def transform_children_to_native(self):
        """
        Recursively replace children with their native representation.

        Sort to get dependency order right, like vtimezone before vevent.
        """
        for child_array in (self.contents[k] for k in self.sort_child_keys()):
            for child in child_array:
                child = child.transform_to_native()
                child.transform_children_to_native()

    def transform_children_from_native(self, clear_behavior=True):
        """
        Recursively transform native children to vanilla representations.
        """
        for child_array in self.contents.values():
            for child in child_array:
                child = child.transform_from_native()
                child.transform_children_from_native(clear_behavior)
                if clear_behavior:
                    child.behavior = None
                    child.parent_behavior = None

    def __repr__(self):
        return f"<{self.name or '*unnamed*'}| {self.get_sorted_children()}>"

    def pretty_print(self, level=0, tabwidth=3):
        pre = " " * level * tabwidth
        print(pre, self.name)
        if isinstance(self, Component):
            for line in self.get_children():
                line.pretty_print(level + 1, tabwidth)


# --------- Parsing functions and parse_line regular expressions ----------------

# Note that underscore is not legal for names, it's included because
# Lotus Notes uses it
patterns = {"name": "[a-zA-Z0-9_-]+", "safe_char": '[^";:,]', "qsafe_char": '[^"]'}
# the combined Python string replacement and regex syntax is a little confusing;
# remember that {foobar} is replaced with patterns['foobar'], so for instance
# param_value is any number of safe_chars or any number of qsaf_chars surrounded
# by double quotes.

patterns["param_value"] = ' "{qsafe_char!s} * " | {safe_char!s} * '.format(**patterns)

# get a tuple of two elements, one will be empty, the other will have the value
patterns["param_value_grouped"] = (
    """
" ( {qsafe_char!s} * )" | ( {safe_char!s} + )
""".format(
        **patterns
    )
)

# get a parameter and its values, without any saved groups
patterns["param"] = (
    r"""
; (?: {name!s} )                     # parameter name
(?:
    (?: = (?: {param_value!s} ) )?   # 0 or more parameter values, multiple
    (?: , (?: {param_value!s} ) )*   # parameters are comma separated
)*
""".format(
        **patterns
    )
)

# get a parameter, saving groups for name and value (value still needs parsing)
patterns["params_grouped"] = (
    r"""
; ( {name!s} )

(?: =
    (
        (?:   (?: {param_value!s} ) )?   # 0 or more parameter values, multiple
        (?: , (?: {param_value!s} ) )*   # parameters are comma separated
    )
)?
""".format(
        **patterns
    )
)

# get a full content line, break it up into group, name, parameters, and value
patterns["line"] = (
    r"""
^ ((?P<group> {name!s})\.)?(?P<name> {name!s}) # name group
  (?P<params> ;?(?: {param!s} )* )               # params group (may be empty)
: (?P<value> .* )$                             # value group
""".format(
        **patterns
    )
)

' "%(qsafe_char)s*" | %(safe_char)s* '  # what is this line?? - never assigned?

param_values_re = re.compile(patterns["param_value_grouped"], re.VERBOSE)
params_re = re.compile(patterns["params_grouped"], re.VERBOSE)
line_re = re.compile(patterns["line"], re.DOTALL | re.VERBOSE)
begin_re = re.compile("BEGIN", re.IGNORECASE)


def parse_params(string):
    """
    Parse parameters
    """
    _all = params_re.findall(string)
    all_parameters = []
    for tup in _all:
        param_list = [tup[0]]  # tup looks like (name, values_string)
        for pair in param_values_re.findall(tup[1]):
            # pair looks like ('', value) or (value, '')
            if pair[0] != "":
                param_list.append(pair[0])
            else:
                param_list.append(pair[1])
        all_parameters.append(param_list)
    return all_parameters


def parse_line(line, line_number=None):
    """
    Parse line
    """
    match = line_re.match(line)
    if match is None:
        raise ParseError(f"Failed to parse line: {line!s}", line_number)
    # Underscores are replaced with dash to work around Lotus Notes
    return (
        match.group("name").replace("_", "-"),
        parse_params(match.group("params")),
        match.group("value"),
        match.group("group"),
    )


# logical line regular expressions

patterns["lineend"] = r"(?:\r\n|\r|\n|$)"
patterns["wrap"] = rf"{patterns['lineend']!s} [\t ]"
patterns["logicallines"] = (
    r"""
(
   (?: [^\r\n] | {wrap!s} )*
   {lineend!s}
)
""".format(
        **patterns
    )
)

patterns["wraporend"] = r"({wrap!s} | {lineend!s} )".format(**patterns)

wrap_re = re.compile(patterns["wraporend"], re.VERBOSE)
logical_lines_re = re.compile(patterns["logicallines"], re.VERBOSE)

TEST_LINES = """
Line 0 text
 , Line 0 continued.
Line 1;encoding=quoted-printable:this is an evil=
 evil=
 format.
Line 2 is a new line, it does not start with whitespace.
"""


def get_logical_lines(fp, allow_qp=True):
    """
    Iterate through a stream, yielding one logical line at a time.

    Because many applications still use vCard 2.1, we have to deal with the
    quoted-printable encoding for long lines, as well as the vCard 3.0 and
    vCalendar line folding technique, a whitespace character at the start
    of the line.

    Quoted-printable data will be decoded in the Behavior decoding phase.

    # We're leaving this test in for awhile, because the unittest was ugly and dumb.
    >>> from io import StringIO
    >>> f=StringIO(TEST_LINES)
    >>> for num, line_ in enumerate(get_logical_lines(f)):
    ...     print("Line %s: %s" % (num, line_[0]))
    ...
    Line 0: Line 0 text, Line 0 continued.
    Line 1: Line 1;encoding=quoted-printable:this is an evil=
     evil=
     format.
    Line 2: Line 2 is a new line, it does not start with whitespace.
    """
    if not allow_qp:
        val = fp.read(-1)

        line_number = 1
        for match in logical_lines_re.finditer(val):
            line, n = wrap_re.subn("", match.group())
            if line != "":
                yield line, line_number
            line_number += n

    else:
        quoted_printable = False
        logical_line = get_buffer()
        line_number = 0
        line_start_number = 0
        while True:
            line = fp.readline()
            if line == "":
                break
            line = line.rstrip(Char.CRLF)
            line_number += 1

            if line.rstrip() == "":
                if logical_line.tell() > 0:
                    yield logical_line.getvalue(), line_start_number
                line_start_number = line_number
                logical_line = get_buffer()
                quoted_printable = False
                continue

            if quoted_printable and allow_qp:
                logical_line.write("\n")
                logical_line.write(line)
                quoted_printable = False
            elif line[0] in Char.SPACEORTAB:
                logical_line.write(line[1:])
            elif logical_line.tell() > 0:
                yield logical_line.getvalue(), line_start_number
                line_start_number = line_number
                logical_line = get_buffer()
                logical_line.write(line)
            else:
                logical_line = get_buffer()
                logical_line.write(line)

            # vCard 2.1 allows parameters to be encoded without a parameter name
            # False positives are unlikely, but possible.
            val = logical_line.getvalue()
            if val[-1] == "=" and val.lower().find("quoted-printable") >= 0:
                quoted_printable = True

        if logical_line.tell() > 0:
            yield logical_line.getvalue(), line_start_number


def text_line_to_content_line(text, n=None):
    return ContentLine(*parse_line(text, n), **{"encoded": True, "line_number": n})


def dquote_escape(param):
    """
    Return param, or "param" if ',' or ';' or ':' is in param.
    """
    if '"' in param:
        raise VObjectError("Double quotes aren't allowed in parameter values.")
    for char in ",;:":  # sourcery skip # temp
        if char in param:
            return f'"{param}"'
    return param


def fold_one_line(outbuf: TextIO, input_: str, line_length=75):
    """
    Folding line procedure that ensures multi-byte utf-8 sequences are not broken across lines
    """
    chunks = split_by_size(input_, byte_size=line_length)
    for chunk in chunks:
        outbuf.write(chunk)
    outbuf.write(Char.CRLF)


def default_serialize(obj, buf, line_length):
    """
    Encode and fold obj and its children, write to buf or return a string.
    """
    outbuf = buf or get_buffer()

    if isinstance(obj, Component):
        group_string = "" if obj.group is None else f"{obj.group}."
        if obj.use_begin:
            fold_one_line(outbuf, f"{group_string}BEGIN:{obj.name}", line_length)
        for child in obj.get_sorted_children():
            # validate is recursive, we only need to validate once
            child.serialize(outbuf, line_length, validate=False)
        if obj.use_begin:
            fold_one_line(outbuf, f"{group_string}END:{obj.name}", line_length)

    elif isinstance(obj, ContentLine):
        started_encoded = obj.encoded
        if obj.behavior and not started_encoded:
            obj.behavior.encode(obj)

        s = get_buffer()

        if obj.group is not None:
            s.write(f"{obj.group}.")
        s.write(obj.name.upper())
        keys = sorted(obj.params.keys())
        for key in keys:
            paramstr = ",".join(dquote_escape(p) for p in obj.params[key])
            try:
                s.write(f";{key}={paramstr}")
            except (UnicodeDecodeError, UnicodeEncodeError):
                s.write(f";{key}={paramstr.encode('utf-8')}")
        try:
            s.write(f":{obj.value}")
        except (UnicodeDecodeError, UnicodeEncodeError):
            s.write(f":{obj.value.encode('utf-8')}")
        if obj.behavior and not started_encoded:
            obj.behavior.decode(obj)
        fold_one_line(outbuf, s.getvalue(), line_length)

    return buf or outbuf.getvalue()


class Stack:
    def __init__(self):
        self.stack = []

    def __len__(self):
        return len(self.stack)

    def top(self):
        return self.stack[-1] if self.stack else None

    def top_name(self):
        return self.stack[-1].name if self.stack else None

    def modify_top(self, item):
        top = self.top()
        if top:
            top.add(item)
        else:
            new = Component()
            self.push(new)
            new.add(item)  # add sets behavior for item and children

    def push(self, obj):
        self.stack.append(obj)

    def pop(self):
        return self.stack.pop()


def read_components(stream_or_string, validate=False, transform=True, ignore_unreadable=False, allow_qp=False):
    """
    Generate one Component at a time from a stream.
    """
    if isinstance(stream_or_string, str):
        stream = get_buffer(stream_or_string)
    else:
        stream = stream_or_string

    try:
        stack = Stack()
        version_line = None
        n = 0
        for line, n in get_logical_lines(stream, allow_qp):
            if ignore_unreadable:
                try:
                    vline = text_line_to_content_line(line, n)
                except VObjectError as e:
                    if e.line_number is not None:
                        msg = "Skipped line {line_number}, message: {msg}"
                    else:
                        msg = "Skipped a line, message: {msg}"
                    logger.error(msg.format(**{"line_number": e.line_number, "msg": str(e)}))
                    continue
            else:
                vline = text_line_to_content_line(line, n)
            if vline.name == "VERSION":
                version_line = vline
                stack.modify_top(vline)
            elif vline.name == "BEGIN":
                stack.push(Component(vline.value, group=vline.group))
            elif vline.name == "PROFILE":
                if not stack.top():
                    stack.push(Component())
                stack.top().set_profile(vline.value)
            elif vline.name == "END":
                if len(stack) == 0:
                    err = "Attempted to end the {0} component but it was never opened"
                    raise ParseError(err.format(vline.value), n)

                if vline.value.upper() == stack.top_name():  # START matches END
                    if len(stack) == 1:
                        component = stack.pop()
                        if version_line is not None:
                            component.set_behavior_from_version_line(version_line)
                        else:
                            behavior = get_behavior(component.name)
                            if behavior:
                                component.set_behavior(behavior)
                        if validate:
                            component.validate(raise_exception=True)
                        if transform:
                            component.transform_children_to_native()
                        yield component  # EXIT POINT
                    else:
                        stack.modify_top(stack.pop())
                else:
                    err = "{0} component wasn't closed"
                    raise ParseError(err.format(stack.top_name()), n)
            else:
                stack.modify_top(vline)  # not a START or END line
        if stack.top():
            if stack.top_name() is None:
                logger.warning("Top level component was never named")
            elif stack.top().use_begin:
                raise ParseError(f"Component {(stack.top_name())!s} was never closed", n)
            yield stack.pop()

    except ParseError as e:
        e.input = stream_or_string
        raise


def read_one(stream, validate=False, transform=True, ignore_unreadable=False, allow_qp=False):
    """
    Return the first component from stream.
    """
    return next(read_components(stream, validate, transform, ignore_unreadable, allow_qp))


# --------------------------- version registry ---------------------------------
__behavior_registry = {}


def register_behavior(behavior, name=None, default=False, id_=None):
    """
    Register the given behavior.

    If default is True (or if this is the first version registered with this
    name), the version will be the default if no id is given.
    """
    if not name:
        name = behavior.name.upper()
    if id_ is None:
        id_ = behavior.version_string
    if name in __behavior_registry:
        if default:
            __behavior_registry[name].insert(0, (id_, behavior))
        else:
            __behavior_registry[name].append((id_, behavior))
    else:
        __behavior_registry[name] = [(id_, behavior)]


def get_behavior(name, id_=None):
    """
    Return a matching behavior if it exists, or None.

    If id is None, return the default for name.
    """
    name = name.upper()
    if name in __behavior_registry:
        if id_:
            for n, behavior in __behavior_registry[name]:
                if n == id_:
                    return behavior

        return __behavior_registry[name][0][1]
    return None


def new_from_behavior(name, id_=None):
    """
    Given a name, return a behaviored ContentLine or Component.
    """
    name = name.upper()
    behavior = get_behavior(name, id_)
    if behavior is None:
        raise VObjectError(f"No behavior found named {name!s}")
    obj = Component(name) if behavior.is_component else ContentLine(name, [], "")
    obj.behavior = behavior
    obj.is_native = False
    return obj
