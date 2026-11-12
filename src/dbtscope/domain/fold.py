"""The parent of a descriptive table (D-062): the `core` or `connector` table it is folded into.

A table's *place* is its pair (domain, layer). The parent of a descriptive table is found by its
relations, then by its name, and holds only in the table's own place:

1. the distinct candidates (role `core` or `connector`) the table points to through a relation:
   exactly one is the found parent;
2. when there are none or several, the candidates whose stem is the table's stem, or its start up to a
   word boundary (`car` for `car_status`, never `carpet_status`): the longest stem wins, a tie gives none;
   the pool is the candidates of step 1 when several, else every candidate of the table's place;
3. otherwise no parent. A found parent in another domain or layer is no parent.

The stem of a table is its name without the fixed part of the name glob of the kind rule that
classified it (`*_hub`: `vehicle_hub` -> `vehicle`).
"""

from __future__ import annotations

import re
from collections import defaultdict
from collections.abc import Iterable, Sequence

from pydantic import BaseModel

from dbtscope.domain import selectors
from dbtscope.domain.config import Role, Rule
from dbtscope.domain.model import DOMAIN, Relation, Table

PARENT_ROLES = ("core", "connector")
WILDCARDS = re.compile(r"\[[^\]]*\]|[*?]")  # a wildcard, a `[...]` set included


class Member(BaseModel):
    """A table of the universe as the parent rule sees it."""

    model_config = DOMAIN

    id: str
    role: Role
    stem: str
    domain: str
    layer: str

    @property
    def place(self) -> tuple[str, str]:
        """The pair (domain, layer) a parent must share with the table it holds."""
        return (self.domain, self.layer)


def _fixed_parts(pattern: str) -> tuple[str, str] | None:
    """The literal text before the first and after the last wildcard of `pattern`, None without one."""
    found = list(WILDCARDS.finditer(pattern))
    if not found:
        return None
    return pattern[: found[0].start()], pattern[found[-1].end() :]


def stem(table: Table, rule: Rule | None) -> str:
    """The table's name, lower-cased, without the fixed part of the name glob of `rule` that selects it.

    `rule` is the kind rule that classified the table (None for a built-in kind). Without a name glob
    that holds a wildcard (a `path:` selector, an exact name), the stem is the whole name.
    """
    name = table.name.lower()
    selector = next((s for s in rule.match if selectors.matches(table, s)), None) if rule else None
    for pattern in selectors.name_patterns(selector) if selector else ():
        fixed = _fixed_parts(pattern.lower())
        if fixed is None:
            continue
        prefix, suffix = fixed
        if name.startswith(prefix):
            name = name[len(prefix) :]
        if suffix and name.endswith(suffix):
            name = name[: -len(suffix)]
        return name
    return name


def _starts_with_word(name: str, head: str) -> bool:
    """`name` is `head`, or starts with it followed by a character that is not a letter or a digit."""
    return name == head or (name.startswith(head) and not name[len(head)].isalnum())


def _by_name(member: Member, pool: Iterable[Member]) -> str | None:
    """The id of the pool candidate with the longest stem that `member`'s stem starts with; None for a tie."""
    matching = [c for c in pool if c.stem and _starts_with_word(member.stem, c.stem)]
    if not matching:
        return None
    longest = max(len(c.stem) for c in matching)
    best = [c for c in matching if len(c.stem) == longest]
    return best[0].id if len(best) == 1 else None


def parents(members: Sequence[Member], relations: Iterable[Relation]) -> dict[str, str]:
    """Descriptive table id -> parent id; a table without a parent is absent (see the module docstring)."""
    ordered = sorted(members, key=lambda m: m.id)
    candidates = {m.id: m for m in ordered if m.role in PARENT_ROLES}
    pointed: dict[str, set[str]] = defaultdict(set)  # child -> the candidates it points to
    for relation in relations:
        if relation.parent in candidates and relation.parent != relation.child:
            pointed[relation.child].add(relation.parent)
    by_place: dict[tuple[str, str], list[Member]] = defaultdict(list)
    for candidate in candidates.values():
        by_place[candidate.place].append(candidate)

    found: dict[str, str] = {}
    for member in ordered:
        if member.role != "descriptive":
            continue
        targets = pointed.get(member.id, set())
        if len(targets) == 1:
            parent = next(iter(targets))
        else:
            pool = [candidates[i] for i in sorted(targets)] if targets else by_place[member.place]
            parent = _by_name(member, pool)
        if parent is not None and candidates[parent].place == member.place:
            found[member.id] = parent
    return found
