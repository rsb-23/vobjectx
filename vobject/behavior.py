from .base import Component, ContentLine, default_serialize
from .exceptions import NativeError, ValidateError, VObjectError


# ------------------------ Abstract class for behavior --------------------------
class Behavior:
    """
    Behavior (validation, encoding, and transformations) for vobjects.

    Abstract class to describe vobject options, requirements and encodings.

    Behaviors are used for root components like VCALENDAR, for subcomponents
    like VEVENT, and for individual lines in components.

    Behavior subclasses are not meant to be instantiated, all methods should
    be classmethods.

    @cvar name:
        The uppercase name of the object described by the class, or a generic
        name if the class defines behavior for many objects.
    @cvar description:
        A brief excerpt from the RFC explaining the function of the component or
        line.
    @cvar version_string:
        The string associated with the component, for instance, 2.0 if there's a
        line like VERSION:2.0, an empty string otherwise.
    @cvar known_children:
        A dictionary with uppercased component/property names as keys and a
        tuple (min, max, id) as value, where id is the id used by
        L{register_behavior}, min and max are the limits on how many of this child
        must occur.  None is used to denote no max or no id.
    @cvar quoted_printable:
        A boolean describing whether the object should be encoded and decoded
        using quoted printable line folding and character escaping.
    @cvar default_behavior:
        Behavior to apply to ContentLine children when no behavior is found.
    @cvar has_native:
        A boolean describing whether the object can be transformed into a more
        Pythonic object.
    @cvar is_component:
        A boolean, True if the object should be a Component.
    @cvar sort_first:
        The lower-case list of children which should come first when sorting.
    @cvar allow_group:
        Whether or not vCard style group prefixes are allowed.
    """

    name = ""
    description = ""
    version_string = ""
    known_children = {}
    quoted_printable = False
    default_behavior = None
    has_native = False
    is_component = False
    allow_group = False
    force_utc = False
    sort_first = []

    def __init__(self):
        err = "Behavior subclasses are not meant to be instantiated"
        raise VObjectError(err)

    @classmethod
    def validate(cls, obj, raise_exception=False, complain_unrecognized=False):
        """Check if the object satisfies this behavior's requirements.

        @param obj:
            The L{ContentLine<base.ContentLine>} or
            L{Component<base.Component>} to be validated.
        @param raise_exception:
            If True, raise a L{base.ValidateError} on validation failure.
            Otherwise return a boolean.
        @param complain_unrecognized:
            If True, fail to validate if an uncrecognized parameter or child is
            found.  Otherwise log the lack of recognition.

        """
        if not cls.allow_group and obj.group is not None:
            err = f"{obj} has a group, but this object doesn't support groups"
            raise VObjectError(err)
        if isinstance(obj, ContentLine):
            return cls.line_validate(obj, raise_exception, complain_unrecognized)
        elif isinstance(obj, Component):
            count = {}
            for child in obj.get_children():
                if not child.validate(raise_exception, complain_unrecognized):
                    return False
                name = child.name.upper()
                count[name] = count.get(name, 0) + 1
            for key, val in cls.known_children.items():
                if count.get(key, 0) < val[0]:
                    if raise_exception:
                        m = "{0} components must contain at least {1} {2}"
                        raise ValidateError(m.format(cls.name, val[0], key))
                    return False
                if val[1] and count.get(key, 0) > val[1]:
                    if raise_exception:
                        m = "{0} components cannot contain more than {1} {2}"
                        raise ValidateError(m.format(cls.name, val[1], key))
                    return False
            return True
        else:
            err = f"{obj} is not a Component or Contentline"
            raise VObjectError(err)

    @classmethod
    def line_validate(cls, line, raise_exception, complain_unrecognized):
        """Examine a line's parameters and values, return True if valid."""
        # todo: remove used param line, raise_exception, complain_unrecognized
        if any([line, raise_exception, complain_unrecognized]):
            pass
        return True

    @classmethod
    def decode(cls, line):
        if line.encoded:
            line.encoded = 0

    @classmethod
    def encode(cls, line):
        if not line.encoded:
            line.encoded = 1

    @staticmethod
    def transform_to_native(obj):
        """
        Turn a ContentLine or Component into a Python-native representation.

        If appropriate, turn dates or datetime strings into Python objects.
        Components containing VTIMEZONEs turn into VtimezoneComponents.

        """
        return obj

    @staticmethod
    def transform_from_native(obj):
        """
        Inverse of transform_to_native.
        """
        raise NativeError("No transform_from_native defined")

    @staticmethod
    def generate_implicit_parameters(obj):
        """Generate any required information that don't yet exist."""

    @classmethod
    def serialize(cls, obj, buf, line_length, validate=True, *args, **kwargs):
        """
        Set implicit parameters, do encoding, return unicode string.

        If validate is True, raise VObjectError if the line doesn't validate
        after implicit parameters are generated.

        Default is to call base.default_serialize.

        """

        cls.generate_implicit_parameters(obj)
        if validate:
            cls.validate(obj, raise_exception=True)

        if obj.is_native:
            transformed = obj.transform_from_native()
            undo_transform = True
        else:
            transformed = obj
            undo_transform = False

        out = default_serialize(transformed, buf, line_length)
        if undo_transform:
            obj.transform_to_native()
        return out

    @classmethod
    def value_repr(cls, line):
        """return the representation of the given content line value"""
        return line.value
