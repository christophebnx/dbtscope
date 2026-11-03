"""Browser tests (D-019): the generated page driven in headless Chromium with Python Playwright.

Skipped when Playwright is not installed (`uv sync --group browser`): every test of this folder is
marked skip at collection, so `pytest -m browser tests/browser` reports skips instead of crashing.
Chromium is never installed by the tooling: it comes from `PLAYWRIGHT_BROWSERS_PATH`, or from
`DBTSCOPE_CHROMIUM` (an executable path).
The CDN scripts of the page (D-014) are downloaded once with `urllib` (TLS verified, proxy honoured)
into the pytest cache and served to the page through `page.route`; every other request is aborted.
"""

from __future__ import annotations

import json
import os
import re
import urllib.request
from collections.abc import Callable, Iterator
from pathlib import Path
from typing import Any

import pytest

from dbtscope import cli
from dbtscope.render.page import LIBRARIES

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
def cdn(request: pytest.FixtureRequest) -> dict[str, bytes]:
    """{url: script body} for every `<script src>` of the page, cached in `.pytest_cache`."""
    urls = [lib.url for lib in LIBRARIES]
    folder = Path(request.config.cache.mkdir("cdn"))
    scripts = {}
    for url in urls:
        cached = folder / re.sub(r"[^A-Za-z0-9._-]", "_", url.split("://", 1)[1])
        if not cached.exists() or not cached.stat().st_size:
            with urllib.request.urlopen(url, timeout=60) as response:
                body = response.read()
            tmp = cached.with_suffix(".part")
            tmp.write_bytes(body)
            tmp.replace(cached)
        scripts[url] = cached.read_bytes()
    return scripts


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

    def state(self) -> dict[str, Any]:
        return self.page.evaluate("views.universe.trajectoryState()")


@pytest.fixture
def open_page(browser: Any, cdn: dict[str, bytes]) -> Iterator[Callable[..., Page]]:
    """open_page(html_path) -> Page, with the universe view started; checks no error was reported."""
    opened: list[Page] = []

    def route(r: Any) -> None:
        url = r.request.url
        if url in cdn:
            r.fulfill(body=cdn[url], content_type="application/javascript")
        elif url.startswith("file:"):
            r.continue_()
        else:
            r.abort()

    def _open(html: Path, viewport: dict[str, int] | None = None) -> Page:
        context = browser.new_context(viewport=viewport or VIEWPORT)
        page = context.new_page()
        wrapped = Page(page)
        page.on("console", lambda m: m.type == "error" and wrapped.errors.append(m.text))
        page.on("pageerror", lambda e: wrapped.errors.append(str(e)))
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
def build_page(dbt_project: Path) -> Callable[[str], tuple[Path, dict[str, Any]]]:
    """Generate the shop page with an optional `dbt-erd.yml`; return it and its embedded payload."""

    def build(config: str = "") -> tuple[Path, dict[str, Any]]:
        if config:
            (dbt_project / "dbt-erd.yml").write_text(config, encoding="utf-8")
        assert cli.main(["--project-dir", str(dbt_project), "--no-parse", "--no-open"]) == 0
        html = dbt_project / "erd_output" / "erd.html"
        text = html.read_text(encoding="utf-8")
        data = json.loads(text.split('<script type="application/json" id="data">')[1].split("</script>")[0])
        return html, data

    return build
