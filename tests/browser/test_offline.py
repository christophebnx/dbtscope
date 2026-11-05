"""Offline page (M2 criterion 1, D-021, D-022) on the synthetic `shop` project.

The page is built with `--offline` (`offline: true` builds the same page, `tests/unit/test_cli.py`)
and opened with the browser offline and every request but the page's own `file:` URL aborted:
d3 and Viz.js must come from the page (svg-pan-zoom left it, D-045).
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from browser.conftest import PAGE_BG, Page, names, only_own_url

pytestmark = pytest.mark.browser

R, G, B = PAGE_BG
# how many pixels of the screen canvas differ from the background (the universe is drawn)
DRAWN = f"""() => {{ const c = document.getElementById('u-canvas'), g = c.getContext('2d');
  const d = g.getImageData(0, 0, c.width, c.height).data; let n = 0;
  for (let i = 0; i < d.length; i += 4)
    if (Math.abs(d[i] - {R}) + Math.abs(d[i + 1] - {G}) + Math.abs(d[i + 2] - {B}) > 30) n++;
  return n; }}"""
UPSTREAM = {"fct_orders", "stg_orders", "dim_customer", "dim_product", "orders"}


def only_own_requests(p: Page, html: Path) -> None:
    own = html.as_uri()
    assert p.requests, "the page itself was requested"
    assert set(p.requests) == {own}, f"requests other than the page: {set(p.requests) - {own}}"


def check_offline_page(p: Page, html: Path, data: dict[str, Any]) -> None:
    p.page.wait_for_function("document.getElementById('u-meta').textContent.length > 0")
    assert p.page.text_content("#u-meta").startswith("6 tables"), p.page.text_content("#u-meta")
    assert p.page.evaluate(DRAWN) > 500, "the universe canvas holds only the background"
    assert p.page.evaluate("[typeof d3.forceSimulation, typeof d3.zoom, typeof Viz]") == ["function"] * 3
    assert p.page.evaluate("typeof svgPanZoom") == "undefined", "svg-pan-zoom left the page (D-045)"
    assert p.page.evaluate("typeof Viz.render") == "function", "full.render.js registered on Viz"

    # trajectory mode from fct_returns: its whole upstream
    p.page.fill("#u-q", "fct_returns")
    p.page.click("#u-traj")
    assert p.page.is_visible("#u-trajbar")
    state = p.state()
    assert state["active"] and state["start"].endswith(".fct_returns")
    assert set(names(state["up"])) == UPSTREAM and state["down"] == {}
    p.page.click("#u-tj-leave")
    assert not p.state()["active"]

    # detail view: Graphviz runs inline, on the main thread, with no worker and no fetch
    p.page.click("#tabs button[data-tab=detail]")
    p.page.wait_for_selector("#d-graph svg g.node", timeout=30_000)
    drawn = set(p.page.eval_on_selector_all("#d-graph svg g.node", "ns => ns.map(n => n.id)"))
    assert drawn == {e["id"] for e in data["detail"]["entities"]} and len(drawn) == 5
    assert p.page.locator("#d-graph svg g.edge").count() == len(data["detail"]["relations"])
    p.page.wait_for_function("!document.getElementById('d-export-svg').disabled")
    only_own_requests(p, html)


def test_offline_page_works_with_every_request_blocked(build_page: Any, open_page: Any) -> None:
    html, data = build_page("", "--offline")
    p = open_page(html, offline=True)
    check_offline_page(p, html, data)  # the fixture then checks no console error was reported


def test_offline_page_exports_images(build_page: Any, open_page: Any) -> None:
    html, _ = build_page("", "--offline")
    p = open_page(html, offline=True)
    name, body = p.download("#u-export")
    assert name == "dbt-ERD-universe.png" and body[:8] == b"\x89PNG\r\n\x1a\n"
    p.page.click("#tabs button[data-tab=detail]")
    p.page.wait_for_function("!document.getElementById('d-export-svg').disabled", timeout=30_000)
    name, body = p.download("#d-export-svg")
    assert name == "dbt-ERD-detail.svg" and b"<svg" in body
    name, body = p.download("#d-export-png")
    assert name == "dbt-ERD-detail.png" and body[:8] == b"\x89PNG\r\n\x1a\n"
    only_own_requests(p, html)


def test_the_blocking_is_real_the_cdn_page_cannot_start(build_page: Any, browser: Any) -> None:
    """Negative control: the default (CDN) page opened the same way has no libraries."""
    html, _ = build_page()
    context = browser.new_context(viewport={"width": 1280, "height": 800})
    try:
        context.set_offline(True)
        page = context.new_page()
        errors: list[str] = []
        page.on("pageerror", lambda e: errors.append(str(e)))
        only_own_url(page, html.as_uri())
        page.goto(html.as_uri())
        page.wait_for_timeout(300)
        assert page.evaluate("typeof d3") == "undefined"
        assert errors, "the CDN page should fail without its libraries"
    finally:
        context.close()
