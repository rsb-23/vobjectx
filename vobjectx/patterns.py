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
