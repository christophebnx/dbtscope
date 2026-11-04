"""Base error of the domain layer, and the one-line message of a validation error."""

from __future__ import annotations

from collections.abc import Iterable

from pydantic import ValidationError
from pydantic_core import ErrorDetails

# pydantic error type -> problem, phrased for a dbt user (D-004: one readable line)
PROBLEMS = {
    "missing": "is required",
    "bool_type": "must be true or false",
    "bool_parsing": "must be true or false",
    "string_type": "must be a string",
    "list_type": "must be a list",
    "tuple_type": "must be a list",
    "dict_type": "must be a mapping",
    "model_type": "must be a mapping",
    "model_attributes_type": "must be a mapping",
}

Location = tuple[str | int, ...]


class DomainError(ValueError):
    """A business rule refused an input. Every domain module's error class derives from it."""


def lower_first(text: str) -> str:
    """`text` with its first letter in lower case: a reason or problem quoted inside a message (D-029)."""
    return text[:1].lower() + text[1:]


def in_words(values: Iterable[str]) -> str:
    """`a, b or c`: a list of choices as a message or a help sentence writes it (D-029)."""
    items = list(values)
    if len(items) < 2:
        return "".join(items)
    return f"{', '.join(items[:-1])} or {items[-1]}"


def _location(parts: Location) -> str:
    """`a.b[0]` for list indexes, `nodes['model.shop.x']` for keys holding a dot (unique_ids)."""
    text = ""
    for part in parts:
        if isinstance(part, int):
            text += f"[{part}]"
        elif "." in part:
            text += f"[{part!r}]"
        else:
            text += f".{part}" if text else part
    return text


def _problem(error: ErrorDetails) -> str:
    """The problem of one pydantic error, without its location."""
    kind = error["type"]
    if kind in PROBLEMS:
        return PROBLEMS[kind]
    if kind == "literal_error":
        return f"must be {error['ctx']['expected']}"
    if kind == "value_error":
        return str(error["ctx"]["error"])
    return lower_first(str(error["msg"]))


def validation_message(error: ValidationError, prefix: Location = ()) -> str:
    """One line for a pydantic error: `<location>: <problem>` of the first problem, and how many more.

    `prefix` is prepended to the location (e.g. `("nodes", unique_id)` for a manifest entry
    validated on its own).
    """
    first = error.errors()[0]
    location = _location(prefix + tuple(first["loc"]))
    message = f"{location}: {_problem(first)}" if location else _problem(first)
    more = error.error_count() - 1
    return message + (f" (and {more} more problem{'s' if more > 1 else ''})" if more else "")
