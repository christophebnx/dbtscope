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
import random
import re
from collections.abc import Callable, Iterator
from pathlib import Path
from typing import Any

import pytest
from conftest import empty_detail, empty_universe, page_of, write_config, write_example
from large_project import write_large_project

from dbtscope.domain.config import merge_config
from dbtscope.domain.payload import (
    DetailEntity,
    DetailKind,
    DetailPayload,
    DetailRelation,
    UniversePayload,
)
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


def dstate(p: Page) -> dict[str, Any]:
    return p.page.evaluate("views.detail.state()")


def name_px(p: Page) -> float:
    """The size on screen of a 16 pt table name: 16 x the zoom scale x the scale Graphviz put on its graph."""
    return p.page.evaluate(
        """() => {
          const scale = el => +(/scale\\(([-\\d.e]+)/.exec(el.getAttribute('transform') || '') || [0, 1])[1];
          const svg = document.querySelector('#d-graph svg');
          return 16 * scale(svg.querySelector(':scope > g')) * scale(svg.querySelector('g.graph'));
        }"""
    )


def entities(data: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {e["id"]: e for e in data["detail"]["entities"]}


def wait_drawn(p: Page) -> None:
    """Wait for the next drawing of the detail (its export buttons come back on)."""
    wait_exportable(p)
    p.page.wait_for_function("views.detail.state().layoutMs > 0")


def double_click(p: Page, table_id: str) -> None:
    p.page.evaluate(
        "id => document.getElementById(id).dispatchEvent(new MouseEvent('dblclick', { bubbles: true }))",
        table_id,
    )
    wait_drawn(p)


def tooltip(p: Page, table_id: str) -> str:
    return p.page.evaluate(
        """id => [...document.getElementById(id).querySelectorAll('*')]
          .map(e => e.getAttributeNS('http://www.w3.org/1999/xlink', 'title')).find(Boolean)""",
        table_id,
    )


def vehicle_hub(data: dict[str, Any], links: int = 2) -> str:
    """A `vehicle` hub with at least `links` links of the group and one folded satellite."""
    by_id = entities(data)
    count: dict[str, int] = {}
    for r in data["detail"]["relations"]:
        if by_id[r["child"]]["kind"] == "link" and by_id[r["child"]]["group"] == "vehicle":
            count[r["parent"]] = count.get(r["parent"], 0) + 1
    held = {e["parent"] for e in by_id.values() if e["parent"]}
    return next(
        i for i in sorted(count) if count[i] >= links and i in held and by_id[i]["group"] == "vehicle"
    )


def untick(p: Page, label: str) -> None:
    p.page.locator("#d-types label", has_text=label).locator("input").click()
    wait_drawn(p)


def centre(p: Page, table_id: str) -> tuple[float, float]:
    """The centre of a drawn table, from its polygons, in Graphviz points."""
    return p.page.evaluate(
        """id => {
          const pts = [...document.getElementById(id).querySelectorAll('polygon')]
            .flatMap(q => q.getAttribute('points').trim().split(/\\s+/).map(t => t.split(',').map(Number)));
          const xs = pts.map(t => t[0]), ys = pts.map(t => t[1]);
          return [(Math.min(...xs) + Math.max(...xs)) / 2, (Math.min(...ys) + Math.max(...ys)) / 2];
        }""",
        table_id,
    )


def universe_page(
    folder: Path, universe: UniversePayload, layout: dict[str, Any] | None = None, **config: Any
) -> Path:
    """Write the page of a synthetic universe payload (empty detail view, optional layout) into `folder`."""
    html = folder / "erd.html"
    settings = merge_config({}, {"view": "universe", "title": "perf", **config})
    html.write_text(render_page(empty_detail("perf"), universe, settings, layout), encoding="utf-8")
    return html


def detail_page(
    folder: Path, detail: DetailPayload, layout: dict[str, Any] | None = None, **config: Any
) -> Path:
    """Write the page of a synthetic detail payload (empty universe, optional layout) into `folder`."""
    html = folder / "erd.html"
    settings = merge_config({}, {"view": "universe", "title": detail.title, **config})
    html.write_text(render_page(detail, empty_universe(), settings, layout), encoding="utf-8")
    return html


def synthetic_detail(
    hubs: int, links: int, sats: int, seed: int = 1500, title: str = "synth"
) -> DetailPayload:
    """One detail group of `hubs` hubs, `links` links of 2 or 3 hubs and `sats` satellites, each folding into
    one hub or link (1 to 5 per parent where the count allows), from `random.Random(seed)`: the worst case of
    the skeleton's budget (300 / 300 / 900 is 1,500 tables, 600 of them drawn)."""
    rng = random.Random(seed)
    kinds = (
        DetailKind(key="hub", label="Hub", color="#2f6fb5", bg="#e3ecf7", role="core"),
        DetailKind(key="link", label="Link", color="#2e8b57", bg="#e2f1e8", role="connector"),
        DetailKind(key="sat", label="Satellite", color="#b8902f", bg="#f6efdc", role="descriptive"),
    )
    columns = (
        ("hk", "varchar", True, ""),
        ("load_date", "timestamp", False, ""),
        ("source", "varchar", False, ""),
    )
    ids = {
        "hub": [f"model.s.h{i:04d}_hub" for i in range(hubs)],
        "link": [f"model.s.l{i:04d}_link" for i in range(links)],
    }
    parents = ids["hub"] + ids["link"]
    counts = dict.fromkeys(
        rng.sample(parents, min(sats, len(parents))), 1
    )  # every parent first, then at random
    while sum(counts.values()) < min(sats, 5 * len(parents)):
        parent = rng.choice(parents)
        counts[parent] = min(5, counts.get(parent, 0) + 1)
    owner = [parent for parent, n in counts.items() for _ in range(n)]
    entities, relations = [], []
    for kind in ("hub", "link"):
        for uid in ids[kind]:
            entities.append(
                DetailEntity(
                    id=uid, name=uid.rsplit(".", 1)[1], group="g", kind=kind, description="", columns=columns
                )
            )
    for i, parent in enumerate(owner):
        uid = f"model.s.s{i:04d}_sat"
        entities.append(
            DetailEntity(
                id=uid,
                name=uid.rsplit(".", 1)[1],
                group="g",
                kind="sat",
                description="",
                columns=columns,
                parent=parent,
            )
        )
        relations.append(DetailRelation(child=uid, parent=parent, column="hk"))
    for uid in ids["link"]:
        for hub in rng.sample(ids["hub"], rng.choice((2, 3))):
            relations.append(DetailRelation(child=uid, parent=hub, column="hk"))
    entities.sort(key=lambda e: e.name)
    return DetailPayload(
        title=title,
        lang="en",
        grouped=False,
        kinds=kinds,
        entities=tuple(entities),
        relations=tuple(relations),
    )


def fan_detail(
    fans: list[list[str]], lang: str = "en", title: str = "fan", extra_hubs: int = 0
) -> DetailPayload:
    """One detail group of hubs, each with its folded tables: `fans[i]` lists the kind keys (`sat`, `pit`,
    `ref`: descriptive; `ref` is labelled "Ref sat") of the tables folding into hub `i`, and `extra_hubs` hubs
    have none. A builder for the rows, tooltip and threshold tests."""
    kinds = (
        DetailKind(key="hub", label="Hub", color="#2f6fb5", bg="#e3ecf7", role="core"),
        DetailKind(key="sat", label="Satellite", color="#b8902f", bg="#f6efdc", role="descriptive"),
        DetailKind(key="pit", label="PIT", color="#8a5fb5", bg="#eee6f7", role="descriptive"),
        DetailKind(key="ref", label="Ref sat", color="#b5602f", bg="#f7e9e0", role="descriptive"),
    )
    columns = (("hk", "varchar", True, ""), ("load_date", "timestamp", False, ""))
    entities, relations = [], []
    for i in range(len(fans) + extra_hubs):
        hub = f"model.s.h{i:03d}_hub"
        entities.append(
            DetailEntity(id=hub, name=f"h{i:03d}_hub", group="g", kind="hub", description="", columns=columns)
        )
        for j, kind in enumerate(fans[i] if i < len(fans) else []):
            uid = f"model.s.h{i:03d}_{kind}{j:04d}"
            entities.append(
                DetailEntity(
                    id=uid,
                    name=uid.rsplit(".", 1)[1],
                    group="g",
                    kind=kind,
                    description="",
                    columns=columns,
                    parent=hub,
                )
            )
            relations.append(DetailRelation(child=uid, parent=hub, column="hk"))
    return DetailPayload(
        title=title,
        lang=lang,
        grouped=False,
        kinds=kinds,
        entities=tuple(sorted(entities, key=lambda e: e.name)),
        relations=tuple(relations),
    )


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


def summary(p: Page) -> dict[str, float]:
    """The summary-card rule of the page (D-063): `cell`, `scale` (cards fully on up to), `stars` (stars
    fully on from) and `alpha` (the cards' opacity at the current zoom)."""
    return p.page.evaluate("views.universe.geometry().summary")


def to_stars(p: Page, key: str | None = None, wait_ms: int = 300) -> None:
    """Set the camera to the stars scale, where the large page draws its stars: centred on the constellation
    `key`, or on what the view's centre shows now. Waits `wait_ms` for the frame."""
    p.page.evaluate(
        """key => { const u = views.universe, c = u.camera(), g = u.geometry(),
          v = document.getElementById('u-canvas'), k = g.summary.stars,
          d = g.constellations.find(d => d.key === key),
          x = d ? d.x : (v.clientWidth / 2 - c.x) / c.k, y = d ? d.y : (v.clientHeight / 2 - c.y) / c.k;
          u.camera({ x: v.clientWidth / 2 - x * k, y: v.clientHeight / 2 - y * k, k }); }""",
        key,
    )
    p.page.wait_for_timeout(wait_ms)


def geometry(p: Page, level: str | None = None) -> dict[str, Any]:
    """The universe's `geometry()` hook, after selecting the detail `level` (names, keys, all) if given."""
    if level:
        p.page.select_option("#u-detail", level)
    return p.page.evaluate("views.universe.geometry()")


def search(p: Page, name: str) -> None:
    """Find `name` with the universe's search box: it centres the table at a scale of at least 1.5."""
    p.page.fill("#u-q", name)
    p.page.dispatch_event("#u-q", "change")
    p.page.wait_for_timeout(CENTRE_WAIT_MS)


def meta(p: Page) -> str:
    """The universe's meta line."""
    return p.page.inner_text("#u-meta")


def set_config(project: Path, *, language: str | None = None, fold: bool | None = None) -> Path:
    """Rewrite the project's `dbt-erd.yml` for the page language and / or the `universe.fold` default; return
    the project. An existing `language:` line is replaced, else one is appended; `fold` appends a `universe:`
    block."""
    path = project / "dbt-erd.yml"
    text = path.read_text(encoding="utf-8")
    if language is not None:
        text, found = re.subn(r"^language: .*$", f"language: {language}", text, flags=re.MULTILINE)
        text += "" if found else f"language: {language}\n"
    if fold is not None:
        text += f"universe:\n  fold: {str(fold).lower()}\n"
    path.write_text(text, encoding="utf-8")
    return project


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


@pytest.fixture
def large_page_shown(tmp_path: Path, open_page: Callable[..., Page]) -> tuple[Page, dict[str, Any]]:
    """The large project's page with `universe.fold: false`: every table drawn, as before M8.2 (D-062)."""
    html, data = page_of(set_config(write_large_project(tmp_path / "large"), fold=False))
    return open_page(html), data


@pytest.fixture
def large(large_page: tuple[Page, dict[str, Any]]) -> tuple[Page, dict[str, Any]]:
    """The folded large page (the default state), under the short name the fold tests use."""
    return large_page


@pytest.fixture
def large_detail(large_page: tuple[Page, dict[str, Any]]) -> tuple[Page, dict[str, Any]]:
    """The large project's page with the detail tab shown (it opens on the `vehicle` skeleton, D-071)."""
    p, data = large_page
    show_detail(p)
    return p, data


@pytest.fixture
def large_project(tmp_path: Path) -> Path:
    """The large generated project written into `tmp_path`, its page not built yet."""
    return write_large_project(tmp_path / "large")
