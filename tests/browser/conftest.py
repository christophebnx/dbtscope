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

import json
import os
from collections.abc import Callable, Iterator
from pathlib import Path
from typing import Any

import pytest

from dbtscope import cli
from dbtscope.render.page import LIBRARIES, VENDOR

try:
    from playwright import sync_api
except ImportError:  # the `browser` dependency group is not installed
    sync_api = None

VIEWPORT = {"width": 1280, "height": 800}
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


@pytest.fixture
def open_page(browser: Any, cdn: dict[str, bytes]) -> Iterator[Callable[..., Page]]:
    """open_page(html_path, viewport, scale, offline) -> Page, with the universe view started.

    `scale` is the device pixel ratio. `offline` blocks every request but the page itself (no CDN
    fulfilment, so a library that was not embedded fails the test). Checks no error was reported."""
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
        html: Path, viewport: dict[str, int] | None = None, scale: float = 1, offline: bool = False
    ) -> Page:
        context = browser.new_context(
            viewport=viewport or VIEWPORT, device_scale_factor=scale, accept_downloads=True
        )
        page = context.new_page()
        wrapped = Page(page)
        page.on("console", lambda m: m.type == "error" and wrapped.errors.append(m.text))
        page.on("pageerror", lambda e: wrapped.errors.append(str(e)))
        page.on("request", lambda r: wrapped.requests.append(r.url))
        if offline:
            context.set_offline(True)
            own = html.as_uri()
            page.route("**/*", lambda r: r.continue_() if r.request.url == own else r.abort())
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
            (dbt_project / "dbt-erd.yml").write_text(config, encoding="utf-8")
        assert cli.main(["--project-dir", str(dbt_project), "--no-parse", "--no-open", *args]) == 0
        html = dbt_project / "erd_output" / "erd.html"
        text = html.read_text(encoding="utf-8")
        data = json.loads(text.split('<script type="application/json" id="data">')[1].split("</script>")[0])
        return html, data

    return build
