"""Definitions and behavior for vCard 3.0"""

from .base import ContentLine, register_behavior
from .behavior import Behavior
from .helper import backslash_escape, byte_decoder, byte_encoder
from .icalendar import string_to_text_values

# ------------------------ vCard structs ---------------------------------------


class Name:
    def __init__(self, family="", given="", additional="", prefix="", suffix=""):
        """
        Each name attribute can be a string or a list of strings.
        """
        self.family = family
        self.given = given
        self.additional = additional
        self.prefix = prefix
        self.suffix = suffix

    @staticmethod
    def to_string(val):
        """
        Turn a string or array value into a string.
        """
        return " ".join(val) if type(val) in (list, tuple) else val

    def __str__(self):
        eng_order = ("prefix", "given", "additional", "family", "suffix")
        return " ".join(self.to_string(getattr(self, val)) for val in eng_order)

    def __repr__(self):
        return f"<Name: {self!s}>"

    def __eq__(self, other):
        try:
            return (
                self.family == other.family
                and self.given == other.given
                and self.additional == other.additional
                and self.prefix == other.prefix
                and self.suffix == other.suffix
            )
        except AttributeError:
            return False


class Address:
    def __init__(self, street="", city="", region="", code="", country="", box="", extended=""):
        """
        Each name attribute can be a string or a list of strings.
        """
        self.box = box
        self.extended = extended
        self.street = street
        self.city = city
        self.region = region
        self.code = code
        self.country = country

    @staticmethod
    def to_string(val, join_char="\n"):
        """
        Turn a string or array value into a string.
        """
        return join_char.join(val) if type(val) in (list, tuple) else val

    lines = ("box", "extended", "street")
    one_line = ("city", "region", "code")

    def __str__(self):
        lines = "\n".join(self.to_string(getattr(self, val)) for val in self.lines if getattr(self, val))
        one_line = tuple(self.to_string(getattr(self, val), " ") for val in self.one_line)
        lines += "\n{0!s}, {1!s} {2!s}".format(*one_line)
        if self.country:
            lines += "\n" + self.to_string(self.country)
        return lines

    def __repr__(self):
        return f"<Address: {self!s}>"

    def __eq__(self, other):
        try:
            return (
                self.box == other.box
                and self.extended == other.extended
                and self.street == other.street
                and self.city == other.city
                and self.region == other.region
                and self.code == other.code
                and self.country == other.country
            )
        except AttributeError:
            return False


# ------------------------ Registered Behavior subclasses ----------------------


class VCardTextBehavior(Behavior):
    """
    Provide backslash escape encoding/decoding for single valued properties.

    TextBehavior also deals with base64 encoding if the ENCODING parameter is
    explicitly set to BASE64.
    """

    allow_group = True
    base64string = "B"

    @classmethod
    def decode(cls, line):
        """
        Remove backslash escaping from line.value_decode line, either to remove
        backslash espacing, or to decode base64 encoding. The content line should
        contain a ENCODING=b for base64 encoding, but Apple Addressbook seems to
        export a singleton parameter of 'BASE64', which does not match the 3.0
        vCard spec. If we encouter that, then we transform the parameter to
        ENCODING=b
        """
        if line.encoded:
            if "BASE64" in line.singletonparams:
                line.singletonparams.remove("BASE64")
                line.encoding_param = cls.base64string
            encoding = getattr(line, "encoding_param", None)
            if encoding:
                line.value = byte_decoder(line.value, "base64")
            else:
                line.value = string_to_text_values(line.value)[0]
            line.encoded = False

    @classmethod
    def encode(cls, line):
        """
        Backslash escape line.value.
        """
        if not line.encoded:
            encoding = getattr(line, "encoding_param", None)
            if encoding and encoding.upper() == cls.base64string:
                if isinstance(line.value, bytes):
                    line.value = byte_encoder(line.value).decode("utf-8").replace("\n", "")
                else:
                    line.value = byte_encoder(line.value.encode(encoding)).decode("utf-8")
            else:
                line.value = backslash_escape(line.value)
            line.encoded = True


class VCardBehavior(Behavior):
    allow_group = True
    default_behavior = VCardTextBehavior


class VCard3(VCardBehavior):
    """
    vCard 3.0 behavior.
    """

    name = "VCARD"
    description = "vCard 3.0, defined in rfc2426"
    version_string = "3.0"
    is_component = True
    sort_first = ("version", "prodid", "uid")
    known_children = {
        "N": (0, 1, None),  # min, max, behavior_registry id
        "FN": (1, None, None),
        "VERSION": (1, 1, None),  # required, auto-generated
        "PRODID": (0, 1, None),
        "LABEL": (0, None, None),
        "UID": (0, None, None),
        "ADR": (0, None, None),
        "ORG": (0, None, None),
        "PHOTO": (0, None, None),
        "CATEGORIES": (0, None, None),
        "GEO": (0, None, None),
    }

    @classmethod
    def generate_implicit_parameters(cls, obj):
        """
        Create PRODID, VERSION, and VTIMEZONEs if needed.

        VTIMEZONEs will need to exist whenever TZID parameters exist or when
        datetimes with tzinfo exist.
        """
        if not hasattr(obj, "version"):
            obj.add(ContentLine("VERSION", [], cls.version_string))


register_behavior(VCard3, default=True)


class FN(VCardTextBehavior):
    name = "FN"
    description = "Formatted name"


register_behavior(FN)


class Label(VCardTextBehavior):
    name = "Label"
    description = "Formatted address"


register_behavior(Label)


class GEO(VCardBehavior):
    name = "GEO"
    description = "Geographical location"


register_behavior(GEO)

WACKY_APPLE_PHOTO_SERIALIZE = True
REALLY_LARGE = 1e50


class Photo(VCardTextBehavior):
    name = "Photo"
    description = "Photograph"

    @classmethod
    def value_repr(cls, line):
        return f" (BINARY PHOTO DATA at 0x{id(line.value)!s}) "

    @classmethod
    def serialize(cls, obj, buf, line_length, validate=True, *args, **kwargs):
        """
        Apple's Address Book is *really* weird with images, it expects
        base64 data to have very specific whitespace.  It seems Address Book
        can handle PHOTO if it's not wrapped, so don't wrap it.
        """
        if WACKY_APPLE_PHOTO_SERIALIZE:
            line_length = REALLY_LARGE
        VCardTextBehavior.serialize(obj, buf, line_length, validate, *args, **kwargs)


register_behavior(Photo)


def to_list_or_string(string):
    string_list = string_to_text_values(string)
    return string_list[0] if len(string_list) == 1 else string_list


def split_fields(string):
    """
    Return a list of strings or lists from a Name or Address.
    """
    return [to_list_or_string(i) for i in string_to_text_values(string, list_separator=";", char_list=";")]


def to_list(string_or_list):
    return [string_or_list] if isinstance(string_or_list, str) else string_or_list


def serialize_fields(obj, order=None):
    """
    Turn an object's fields into a ';' and ',' seperated string.

    If order is None, obj should be a list, backslash escape each field and
    return a ';' separated string.
    """
    fields = []
    if order is None:
        fields = [backslash_escape(val) for val in obj]
    else:
        for field in order:
            escaped_value_list = [backslash_escape(val) for val in to_list(getattr(obj, field))]
            fields.append(",".join(escaped_value_list))
    return ";".join(fields)


NAME_ORDER = ("family", "given", "additional", "prefix", "suffix")
ADDRESS_ORDER = ("box", "extended", "street", "city", "region", "code", "country")


class NameBehavior(VCardBehavior):
    """
    A structured name.
    """

    has_native = True

    @staticmethod
    def transform_to_native(obj):
        """
        Turn obj.value into a Name.
        """
        if obj.is_native:
            return obj
        obj.is_native = True
        obj.value = Name(**dict(zip(NAME_ORDER, split_fields(obj.value))))
        return obj

    @staticmethod
    def transform_from_native(obj):
        """
        Replace the Name in obj.value with a string.
        """
        obj.is_native = False
        obj.value = serialize_fields(obj.value, NAME_ORDER)
        return obj


register_behavior(NameBehavior, "N")


class AddressBehavior(VCardBehavior):
    """
    A structured address.
    """

    has_native = True

    @staticmethod
    def transform_to_native(obj):
        """
        Turn obj.value into an Address.
        """
        if obj.is_native:
            return obj
        obj.is_native = True
        obj.value = Address(**dict(zip(ADDRESS_ORDER, split_fields(obj.value))))
        return obj

    @staticmethod
    def transform_from_native(obj):
        """
        Replace the Address in obj.value with a string.
        """
        obj.is_native = False
        obj.value = serialize_fields(obj.value, ADDRESS_ORDER)
        return obj


register_behavior(AddressBehavior, "ADR")


class OrgBehavior(VCardBehavior):
    """
    A list of organization values and sub-organization values.
    """

    has_native = True

    @staticmethod
    def transform_to_native(obj):
        """
        Turn obj.value into a list.
        """
        if obj.is_native:
            return obj
        obj.is_native = True
        obj.value = split_fields(obj.value)
        return obj

    @staticmethod
    def transform_from_native(obj):
        """
        Replace the list in obj.value with a string.
        """
        if not obj.is_native:
            return obj
        obj.is_native = False
        obj.value = serialize_fields(obj.value)
        return obj


register_behavior(OrgBehavior, "ORG")
