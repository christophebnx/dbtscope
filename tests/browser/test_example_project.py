"""The page of the example project `acme_retail` (D-033), built from its real `dbt parse` manifest."""

from __future__ import annotations

from collections import Counter
from typing import Any

import pytest
from conftest import EXAMPLE_EXPECTED

from browser.conftest import Page, show_detail, wait_exportable

pytestmark = pytest.mark.browser


def _set_all_columns(p: Page, on: bool) -> None:
    """Switch the detail view to every column (`on`) or to key columns, then wait for the drawing."""
    if (p.page.locator("#d-cols.on").count() == 1) != on:
        p.page.click("#d-cols")
    wait_exportable(p)


def test_example_page_draws_both_views(example_page: tuple[Page, dict[str, Any]]) -> None:
    p, data = example_page
    assert len(data["universe"]["nodes"]) == EXAMPLE_EXPECTED["universe"]["tables"]
    show_detail(p)
    entities = data["detail"]["entities"]
    sizes = Counter(e["group"] for e in entities)
    group_of = {e["id"]: e["group"] for e in entities}
    for group in list(sizes):  # a group also draws the other-group parents its tables point to
        sizes[group] += len(
            {
                r["parent"]
                for r in data["detail"]["relations"]
                if group_of[r["child"]] == group and group_of[r["parent"]] != group
            }
        )
    sizes[""] = len(entities)  # the "all groups" option
    groups = p.page.eval_on_selector_all("#d-group option", "options => options.map(o => o.value)")
    assert sorted(groups) == sorted(sizes)
    for group in groups:
        p.page.select_option("#d-group", group)
        for on in (False, True):
            _set_all_columns(p, on)
            assert p.page.locator("#d-graph svg g.node").count() == sizes[group], (group, on)
            assert "Render error" not in p.page.text_content("#d-graph"), (group, on)
