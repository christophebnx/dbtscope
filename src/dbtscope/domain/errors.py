"""Base error of the domain layer, and the one-line message of a validation error."""

from __future__ import annotations

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
    message = str(error["msg"])
    return message[:1].lower() + message[1:]


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
