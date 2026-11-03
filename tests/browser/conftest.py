"""Browser tests (D-019): the generated page driven in headless Chromium with Python Playwright.

Skipped when Playwright is not installed (`uv sync --group browser`). Chromium is never installed by
the tooling: it comes from `PLAYWRIGHT_BROWSERS_PATH`, or from `DBTSCOPE_CHROMIUM` (an executable path).
The CDN scripts of the page (D-014) are downloaded once with `urllib` (TLS verified, proxy honoured)
into the pytest cache and served to the page through `page.route`; every other request is aborted.
"""

from __future__ import annotations

import os
import re
import urllib.request
from collections.abc import Callable, Iterator
from pathlib import Path
from typing import Any

import pytest

sync_api = pytest.importorskip("playwright.sync_api")

from dbtscope.render.page import ASSETS  # noqa: E402

VIEWPORT = {"width": 1280, "height": 800}


@pytest.fixture(scope="session")
def cdn(request: pytest.FixtureRequest) -> dict[str, bytes]:
    """{url: script body} for every `<script src>` of the page, cached in `.pytest_cache`."""
    urls = re.findall(r'<script src="([^"]+)"', (ASSETS / "page.html").read_text(encoding="utf-8"))
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
