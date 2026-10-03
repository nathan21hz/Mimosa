""" Templates for push messages and URLs, compatible with the str.format templates used before.

    {0} {1}            data by position; {-1} is the last one; {} takes the next position
    {item}             a named variable
    {0[1]} {0[-1]}     list index
    {0[id]} {0.id}     object key
    {0:.2f}            Python format spec (can't be combined with filters, use |format then)
    {0|join:", "}      filters, chained with |; see FILTERS
    {{ }}              literal braces

Only list indexes and object keys can be looked up, never attributes, so a template can't reach
into Python objects the way str.format allows (e.g. "{0.__class__}").
"""
import re
import json
from functools import lru_cache
from urllib.parse import quote


class TemplateError(Exception):
    """ A template can't be parsed or rendered """


# a value that isn't there; only the default filter accepts it
MISSING = object()


def to_text(value):
    """ Text of a value without a format spec, the same as str.format """
    return str(value)


def _default(value, fallback=""):
    return fallback if value is MISSING or value is None or value == "" or value == [] else value


def _join(value, separator=", "):
    if isinstance(value, (list, tuple)):
        return separator.join(to_text(v) for v in value)
    return to_text(value)


def _truncate(value, length):
    text = to_text(value)
    length = int(length)
    return text if len(text) <= length else text[:length] + "…"


def _first(value):
    return value[0] if value else MISSING


def _last(value):
    return value[-1] if value else MISSING


# name -> (function, min arguments, max arguments)
FILTERS = {
    "default": (_default, 0, 1),     # value if not missing / null / "" / [], otherwise the argument
    "join": (_join, 0, 1),           # list items joined by the argument, ", " by default
    "json": (lambda v: json.dumps(v, ensure_ascii=False, default=str), 0, 0),
    "len": (len, 0, 0),
    "upper": (lambda v: to_text(v).upper(), 0, 0),
    "lower": (lambda v: to_text(v).lower(), 0, 0),
    "strip": (lambda v: to_text(v).strip(), 0, 0),
    "truncate": (_truncate, 1, 1),   # at most this many characters, then "…"
    "urlencode": (lambda v: quote(to_text(v), safe=""), 0, 0),
    "first": (_first, 0, 0),
    "last": (_last, 0, 0),
    "format": (lambda v, spec: format(v, spec), 1, 1),   # Python format spec, e.g. ".2f"
}

_ROOT = re.compile(r"-?\d+|[A-Za-z_]\w*")
_KEY = re.compile(r"\[([^\]]*)\]|\.(\w+)")
_FILTER = re.compile(r"([A-Za-z_]\w*)\s*(?::(.*))?$", re.S)


def render(template, args=(), variables=None):
    """ Fill the template with positional data (args) and named variables """
    if not isinstance(template, str):
        raise TemplateError("Template must be a string, got {}.".format(type(template).__name__))
    variables = variables or {}
    return "".join(part if isinstance(part, str) else part.render(args, variables)
                   for part in compile_template(template))


@lru_cache(maxsize=512)
def compile_template(template):
    """ Template text -> tuple of literal strings and Fields """
    parts = []
    literal = []
    auto_index = 0
    i = 0
    while i < len(template):
        char = template[i]
        if char == "{":
            if template.startswith("{{", i):
                literal.append("{")
                i += 2
                continue
            end = _field_end(template, i + 1)
            expression = template[i + 1:end].strip()
            if not expression:
                expression = str(auto_index)
                auto_index += 1
            if literal:
                parts.append("".join(literal))
                literal = []
            parts.append(Field(expression))
            i = end + 1
        elif char == "}":
            if template.startswith("}}", i):
                literal.append("}")
                i += 2
                continue
            raise TemplateError("Single '}}' at position {} of template {!r}, use '}}}}' for a literal one.".format(i, template))
        else:
            literal.append(char)
            i += 1
    if literal:
        parts.append("".join(literal))
    return tuple(parts)


def _field_end(template, start):
    """ Index of the '}' closing the field starting at start, skipping quoted filter arguments """
    quote_char = None
    i = start
    while i < len(template):
        char = template[i]
        if quote_char:
            if char == "\\":
                i += 1
            elif char == quote_char:
                quote_char = None
        elif char in "\"'":
            quote_char = char
        elif char == "}":
            return i
        elif char == "{":
            raise TemplateError("Nested '{{' at position {} of template {!r}.".format(i, template))
        i += 1
    raise TemplateError("Unclosed '{{' at position {} of template {!r}.".format(start - 1, template))


def _split(text, separator):
    """ Split on separator outside quotes and brackets """
    parts, current, quote_char, depth = [], [], None, 0
    i = 0
    while i < len(text):
        char = text[i]
        if quote_char:
            if char == "\\" and i + 1 < len(text):
                current.append(char)
                i += 1
                char = text[i]
            elif char == quote_char:
                quote_char = None
        elif char in "\"'":
            quote_char = char
        elif char == "[":
            depth += 1
        elif char == "]":
            depth -= 1
        elif char == separator and depth == 0:
            parts.append("".join(current))
            current = []
            i += 1
            continue
        current.append(char)
        i += 1
    parts.append("".join(current))
    return parts


def _parse_argument(text):
    text = text.strip()
    if len(text) >= 2 and text[0] == text[-1] and text[0] in "\"'":
        if text[0] == '"':
            # strict=False: a "\n" in a JSON task file arrives here as a real newline
            return json.loads(text, strict=False)
        return text[1:-1].replace("\\'", "'").replace("\\\\", "\\")
    return text


class Field():
    """ One {...} of a template """
    def __init__(self, expression) -> None:
        self.expression = expression
        tokens = _split(expression, "|")
        head = tokens[0].strip()
        self.spec = None
        if len(tokens) == 1:
            head_parts = _split(head, ":")
            if len(head_parts) > 1:
                head = head_parts[0].strip()
                self.spec = ":".join(head_parts[1:])
        self.root, self.keys = self.parse_path(head)
        self.filters = [self.parse_filter(token) for token in tokens[1:]]

    def error(self, message):
        return TemplateError("{{{}}}: {}".format(self.expression, message))

    def parse_path(self, text):
        match = _ROOT.match(text)
        if not match:
            raise self.error("expected a data position (e.g. 0) or a variable name")
        root = int(match.group()) if match.group().lstrip("-").isdigit() else match.group()
        keys = []
        position = match.end()
        while position < len(text):
            key = _KEY.match(text, position)
            if not key:
                raise self.error("can't read '{}'; use [index], [key] or .key".format(text[position:]))
            keys.append(key.group(1) if key.group(1) is not None else key.group(2))
            position = key.end()
        return root, keys

    def parse_filter(self, text):
        match = _FILTER.match(text.strip())
        if not match:
            raise self.error("invalid filter '{}'".format(text.strip()))
        name, argument = match.group(1), match.group(2)
        if name not in FILTERS:
            raise self.error("unknown filter '{}', available: {}".format(name, ", ".join(FILTERS)))
        func, min_args, max_args = FILTERS[name]
        arguments = [] if argument is None else [_parse_argument(argument)]
        if not min_args <= len(arguments) <= max_args:
            raise self.error("filter '{}' takes {} argument(s)".format(
                name, min_args if min_args == max_args else "{}-{}".format(min_args, max_args)))
        return name, func, arguments

    def resolve(self, args, variables):
        """ (value, None), or (MISSING, why) when a data position, index or key isn't there """
        if isinstance(self.root, int):
            if not -len(args) <= self.root < len(args):
                return MISSING, "no data {} (there are {})".format(self.root, len(args))
            value = args[self.root]
        else:
            if self.root not in variables:
                raise self.error("unknown variable '{}'{}".format(
                    self.root, ", available: " + ", ".join(variables) if variables else ""))
            value = variables[self.root]
        for key in self.keys:
            if isinstance(value, dict):
                if key not in value:
                    return MISSING, "no key '{}'".format(key)
                value = value[key]
            elif isinstance(value, (list, tuple)):
                try:
                    index = int(key)
                except ValueError:
                    raise self.error("'{}' is not a number, but the value is a list".format(key))
                if not -len(value) <= index < len(value):
                    return MISSING, "index {} out of range ({} items)".format(index, len(value))
                value = value[index]
            elif value is None:
                return MISSING, "value is null before '{}'".format(key)
            else:
                raise self.error("can't look up '{}' in a {}".format(key, type(value).__name__))
        return value, None

    def render(self, args, variables):
        value, missing = self.resolve(args, variables)
        for name, func, arguments in self.filters:
            if value is MISSING and name != "default":
                raise self.error(missing)
            try:
                value = func(value, *arguments)
            except (TypeError, ValueError) as e:
                raise self.error("filter '{}' failed: {}".format(name, e))
            if value is MISSING:
                missing = "filter '{}' found nothing".format(name)
        if value is MISSING:
            raise self.error(missing + "; add |default to allow it")
        if self.spec is not None:
            try:
                return format(value, self.spec)
            except (TypeError, ValueError) as e:
                raise self.error("format spec '{}' failed: {}".format(self.spec, e))
        return to_text(value)
