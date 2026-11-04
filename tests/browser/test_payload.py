"""The embedded JSON cannot disturb the HTML parser (D-023) on the synthetic `shop` project."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
from conftest import shop_manifest, write_manifest

from browser.conftest import show_detail, wait_exportable

pytestmark = pytest.mark.browser

# "<!-- <script>" in a script block puts the parser in script double-escaped state: an unescaped
# payload would no longer end at its own </script>, and the page scripts after it would never run
DESCRIPTION = "Orders <!-- <script> legacy"


def test_page_starts_with_a_description_holding_a_comment_and_a_script_tag(
    dbt_project: Path, build_page: Any, open_page: Any
) -> None:
    # the data block is the same in the offline page (TWINS of the reference pages, test_page D-023)
    manifest = shop_manifest()
    manifest["nodes"]["model.shop.fct_orders"]["description"] = DESCRIPTION
    write_manifest(dbt_project, manifest)
    html, data = build_page()
    assert DESCRIPTION in {e["description"] for e in data["detail"]["entities"]}
    p = open_page(html)
    p.page.wait_for_function("document.getElementById('u-meta').textContent.length > 0")
    assert p.page.text_content("#u-meta").startswith("6 tables")
    described = "JSON.parse(document.getElementById('data').textContent).detail.entities"
    assert DESCRIPTION in p.page.evaluate(described + ".map(e => e.description)")


def test_detail_draws_columns_without_a_data_type(dbt_project: Path, build_page: Any, open_page: Any) -> None:
    # regression: an untyped column wrote an empty <font></font>, which Graphviz refuses, and the
    # whole detail view showed "Render error: … in label of node …" (most dbt projects type no column)
    manifest = shop_manifest()
    for node in manifest["nodes"].values():
        for column in node.get("columns", {}).values():
            column["data_type"] = None
    write_manifest(dbt_project, manifest)
    html, data = build_page()
    p = open_page(html)
    show_detail(p)  # key columns only
    p.page.click("#d-cols")  # then every column
    wait_exportable(p)
    assert p.page.locator("#d-graph .msg").count() == 0
    assert p.page.locator("#d-graph svg g.node").count() == len(data["detail"]["entities"])
