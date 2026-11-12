"""Browser tests (D-019): the generated page driven in headless Chromium with Python Playwright.

Skipped when Playwright is not installed (`uv sync --group browser`): every test of this folder is
marked skip at collection, so `pytest -m browser tests/browser` reports skips instead of crashing.
Chromium is never installed by the tooling: it comes from `PLAYWRIGHT_BROWSERS_PATH`, or from
`DBTSCOPE_CHROMIUM` (an executable path).
The CDN scripts of the page (D-014) are served through `page.route` from their vendored copies in
`src/dbtscope/render/vendor/` (the same bytes, sha256-checked); every other request is aborted, so the
tests need no network (D-022).
"""

from __future__ import annotations

import os
from collections.abc import Callable, Iterator
from pathlib import Path
from typing import Any

import pytest
from conftest import empty_detail, page_of, write_config, write_example
from large_project import write_large_project

from dbtscope.domain.config import merge_config
from dbtscope.domain.payload import UniversePayload
from dbtscope.render.page import LIBRARIES, VENDOR, render_page

try:
    from playwright import sync_api
except ImportError:  # the `browser` dependency group is not installed
    sync_api = None

VIEWPORT = {"width": 1280, "height": 800}
NARROW = {"width": 360, "height": 800}
PAGE_BG = (0xF5, 0xF6, 0xF8)  # C.bg of universe.js
CENTRE_WAIT_MS = 900  # zoomTo animates for 600 ms
HERE = Path(__file__).parent


def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:
    """Skip the browser tests cleanly when Playwright is absent (a module-level importorskip in a
    conftest aborts the whole collection instead)."""
    if sync_api is not None:
        return
    skip = pytest.mark.skip(reason="Playwright is not installed (uv sync --group browser)")
    for item in items:
        if HERE in item.path.parents:
            item.add_marker(skip)


@pytest.fixture(scope="session")
def cdn() -> dict[str, bytes]:
    """{CDN url: script body} for every library of the page, from its vendored copy (D-022)."""
    return {lib.url: (VENDOR / lib.file).read_bytes() for lib in LIBRARIES}


@pytest.fixture(scope="session")
def browser() -> Iterator[Any]:
    with sync_api.sync_playwright() as p:
        b = p.chromium.launch(executable_path=os.environ.get("DBTSCOPE_CHROMIUM") or None)
        yield b
        b.close()


class Page:
    """A loaded page and the errors it reported (console errors, uncaught exceptions)."""

    def __init__(self, page: Any) -> None:
        self.page = page
        self.errors: list[str] = []
        self.requests: list[str] = []  # every URL the page asked for

    def download(self, selector: str) -> tuple[str, bytes]:
        """Click `selector` and return the (suggested file name, bytes) of the download it starts."""
        with self.page.expect_download() as info:
            self.page.click(selector)
        download = info.value
        return download.suggested_filename, Path(download.path()).read_bytes()

    def state(self) -> dict[str, Any]:
        return self.page.evaluate("views.universe.trajectoryState()")


Shop = tuple[Page, dict[str, Any]]  # the opened shop page and its embedded payload


def only_own_url(page: Any, url: str) -> None:
    """Abort every request of a Playwright page but `url` (its own file)."""
    page.route("**/*", lambda r: r.continue_() if r.request.url == url else r.abort())


def names(ids: dict[str, int]) -> dict[str, int]:
    """{unique_id: distance} -> {table name: distance}."""
    return {uid.rsplit(".", 1)[1]: d for uid, d in ids.items()}


def names_of(data: dict[str, Any], ids: set[str]) -> set[str]:
    """The table names of `ids`, through the detail payload."""
    by_id = {e["id"]: e["name"] for e in data["detail"]["entities"]}
    return {by_id[i] for i in ids}


def wait_exportable(p: Page) -> None:
    """Wait until both detail export buttons are enabled (the diagram is drawn and driven)."""
    p.page.wait_for_function(
        "['d-export-png', 'd-export-svg'].every(i => !document.getElementById(i).disabled)",
        timeout=30_000,
    )


def show_detail(p: Page, exportable: bool = True) -> None:
    """Open the detail tab and wait for the diagram (and, by default, for its export buttons)."""
    p.page.click("#tabs button[data-tab=detail]")
    p.page.wait_for_selector("#d-graph svg g.node", timeout=30_000)
    if exportable:
        wait_exportable(p)


def universe_page(folder: Path, universe: UniversePayload, **config: Any) -> Path:
    """Write the page of a synthetic universe payload (empty detail view) into `folder`; return it."""
    html = folder / "erd.html"
    settings = merge_config({}, {"view": "universe", "title": "perf", **config})
    html.write_text(render_page(empty_detail("perf"), universe, settings), encoding="utf-8")
    return html


def wait_flow(p: Page) -> None:
    """Wait until the flow view is drawn and driven (its export buttons are enabled, M5.3)."""
    p.page.wait_for_function(
        "flow && flow.state().open && !document.getElementById('f-export-svg').disabled", timeout=60_000
    )


def open_flow(p: Page, name: str, direction: str = "both", depth: str = "dall") -> dict[str, Any]:
    """Enter the trajectory of the table `name` with these options, open its flow; return flow.state()."""
    p.page.fill("#u-q", name)
    p.page.click("#u-traj")
    p.page.select_option("#u-tj-dir", direction)
    p.page.select_option("#u-tj-depth", depth)
    p.page.click("#u-tj-flow")
    wait_flow(p)
    return p.page.evaluate("flow.state()")


def close_panel(p: Page, view: str) -> None:
    if p.page.is_visible(f"#{view}-panel"):
        p.page.click(f"#{view}-toggle")
    assert p.page.is_hidden(f"#{view}-panel")


def scroll_width(p: Page) -> int:
    return p.page.evaluate("Math.max(document.documentElement.scrollWidth, document.body.scrollWidth)")


@pytest.fixture
def open_page(browser: Any, cdn: dict[str, bytes]) -> Iterator[Callable[..., Page]]:
    """open_page(html_path, viewport, scale, offline, touch) -> Page, with the universe view started.

    `scale` is the device pixel ratio. `offline` blocks every request but the page itself (no CDN
    fulfilment, so a library that was not embedded fails the test). `touch` emulates a phone (touch
    screen, `pointer: coarse`, M5.2). Checks no error was reported."""
    opened: list[Page] = []

    def route(r: Any) -> None:
        url = r.request.url
        if url in cdn:
            r.fulfill(body=cdn[url], content_type="application/javascript")
        elif url.startswith("file:"):
            r.continue_()
        else:
            r.abort()

    def _open(
        html: Path,
        viewport: dict[str, int] | None = None,
        scale: float = 1,
        offline: bool = False,
        touch: bool = False,
    ) -> Page:
        context = browser.new_context(
            viewport=viewport or VIEWPORT,
            device_scale_factor=scale,
            accept_downloads=True,
            has_touch=touch,
            is_mobile=touch,
        )
        page = context.new_page()
        wrapped = Page(page)
        page.on("console", lambda m: m.type == "error" and wrapped.errors.append(m.text))
        page.on("pageerror", lambda e: wrapped.errors.append(str(e)))
        page.on("request", lambda r: wrapped.requests.append(r.url))
        if offline:
            context.set_offline(True)
            only_own_url(page, html.as_uri())
        else:
            page.route("**/*", route)
        page.goto(html.as_uri())
        page.wait_for_function("typeof views !== 'undefined' && !!views.universe", timeout=60_000)
        opened.append(wrapped)
        return wrapped

    yield _open
    for p in opened:
        errors = list(p.errors)
        p.page.context.close()
        assert errors == [], f"the page reported errors: {errors}"


@pytest.fixture
def build_page(dbt_project: Path) -> Callable[..., tuple[Path, dict[str, Any]]]:
    """Generate the shop page with an optional `dbt-erd.yml` and extra CLI arguments (`--offline`);
    return it and its embedded payload."""

    def build(config: str = "", *args: str) -> tuple[Path, dict[str, Any]]:
        if config:
            write_config(dbt_project, config)
        return page_of(dbt_project, *args)

    return build


@pytest.fixture
def shop_page(build_page: Callable[..., tuple[Path, dict[str, Any]]], open_page: Callable[..., Page]) -> Shop:
    """The default shop page, opened, and its payload."""
    html, data = build_page()
    return open_page(html), data


@pytest.fixture
def example_page(tmp_path: Path, open_page: Callable[..., Page]) -> tuple[Page, dict[str, Any]]:
    """The page of the example project `acme_retail` (D-033), opened, and its payload."""
    html, data = page_of(write_example(tmp_path / "acme_retail"))
    return open_page(html), data


@pytest.fixture
def large_page(tmp_path: Path, open_page: Callable[..., Page]) -> tuple[Page, dict[str, Any]]:
    """The page of the large generated Data Vault project (D-060), opened, and its payload."""
    html, data = page_of(write_large_project(tmp_path / "large"))
    return open_page(html), data
