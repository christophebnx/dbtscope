"""The parent of a descriptive table (D-061): the `core` or `connector` table it is folded into.

Step 1, by relation: the descriptive table has `relationships` tests or foreign keys *from* it to exactly
one candidate. Step 2, by name, when there are none or several: the candidate whose stem is the longest
prefix of the table's own stem, at a non-alphanumeric boundary, among the related candidates (several
relations) or the candidates of the table's domain (none). A tie, no prefix or a parent of another domain
gives no parent: nothing is ever folded arbitrarily.
"""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable, Mapping

from dbtscope.domain import selectors
from dbtscope.domain.config import KindRule
from dbtscope.domain.model import Relation, Table

CANDIDATE_ROLES = ("core", "connector")


def _fixed_parts(glob: str) -> tuple[str, str] | None:
    """The text before and after the single `*` of a glob with no other wildcard, else None."""
    if glob.count("*") != 1 or "?" in glob or "[" in glob:
        return None
    prefix, _, suffix = glob.lower().partition("*")
    return prefix, suffix


def stem(table: Table, rule: KindRule | None) -> str:
    """The name of `table`, lower-cased, without the fixed part of its kind's name glob.

    `*_hub` turns `vehicle_order_hub` into `vehicle_order`, `dim_*` turns `dim_vehicle` into `vehicle`.
    The whole name when the kind has no such glob (a tag selector, several wildcards, a built-in kind);
    "" when nothing is left (the table is named exactly as the fixed part).
    """
    name = table.name.lower()
    if rule is None:
        return name
    selector = next((s for s in rule.match if selectors.matches(table, s)), None)
    glob = selectors.name_glob(selector) if selector is not None else None
    fixed = _fixed_parts(glob) if glob is not None else None
    if fixed is None:
        return name
    prefix, suffix = fixed
    start, end = len(prefix), len(name) - len(suffix)
    return name[start:end] if start < end and name.startswith(prefix) and name.endswith(suffix) else ""


def _prefixes(name: str) -> Iterable[str]:
    """The prefixes of `name` ending at a boundary (its end, or before a non-alphanumeric), longest first."""
    for end in range(len(name), 0, -1):
        if end == len(name) or not name[end].isalnum():
            yield name[:end]


def _by_stem(uids: Iterable[str], stems: Mapping[str, str]) -> dict[str, list[str]]:
    found: dict[str, list[str]] = defaultdict(list)
    for uid in uids:
        if stems[uid]:
            found[stems[uid]].append(uid)
    return found


def _named(own_stem: str, pool: Mapping[str, list[str]]) -> str | None:
    """The one table of `pool` with the longest stem that prefixes `own_stem`; None for none or a tie."""
    for prefix in _prefixes(own_stem):
        if prefix in pool:
            return pool[prefix][0] if len(pool[prefix]) == 1 else None
    return None


def parents(
    tables: Mapping[str, Table],
    kinds: Mapping[str, KindRule | None],
    domains: Mapping[str, str],
    relations: Iterable[Relation],
) -> dict[str, str]:
    """The parent of each folded table: unique_id -> unique_id of its `core` or `connector` table.

    `tables` are the tables in scope, `kinds` the rule that classified each (None for a built-in kind),
    `domains` the domain key of each. Only tables of role `descriptive` are folded, and only into a
    parent of their own domain.
    """
    roles = {uid: getattr(kinds.get(uid), "role", None) for uid in tables}
    candidates = {uid for uid, role in roles.items() if role in CANDIDATE_ROLES}
    related: dict[str, set[str]] = defaultdict(set)
    for relation in relations:
        if relation.parent in candidates:
            related[relation.child].add(relation.parent)
    stems = {uid: stem(tables[uid], kinds.get(uid)) for uid in tables}
    by_domain: dict[str, dict[str, list[str]]] = {}
    for domain in {domains[uid] for uid in candidates}:
        by_domain[domain] = _by_stem(sorted(u for u in candidates if domains[u] == domain), stems)

    found: dict[str, str] = {}
    for uid in sorted(uid for uid, role in roles.items() if role == "descriptive"):
        options = related.get(uid, set())
        if len(options) == 1:
            parent: str | None = next(iter(options))
        elif len(options) > 1:
            parent = _named(stems[uid], _by_stem(sorted(options), stems))
        else:
            parent = _named(stems[uid], by_domain.get(domains[uid], {}))
        if parent is not None and domains[parent] == domains[uid]:
            found[uid] = parent
    return found
