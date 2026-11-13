"""Universe layout (M5.5, D-040): a domain's tables in layer bands, left to right along the data flow,
packed into the smallest disc, with no overlap, reproducible, fast, and old saved arrangements still
applied. Design note: docs/architecture/2026-11-05-m5.5-universe-layout.md (test plan 1 to 9).

Geometry is read through `views.universe.geometry()` (world coordinates: a table's point P is its star
centre, its reserved box is `x ± w/2`, `y + oy ± h/2`); every check is computed here. "acme" is the
example project, "big" the 1,500-table payload of test_trajectory_perf.py.
"""

from __future__ import annotations

import json
import math
import re
from collections import defaultdict
from collections.abc import Callable
from itertools import pairwise
from pathlib import Path
from typing import Any

import pytest
from conftest import SHOP, page_of, write_config, write_example
from reference_pages import LAYOUT as EDGE_LAYOUT
from reference_pages import build_page as reference_page

from browser.conftest import Page, universe_page
from browser.test_trajectory_perf import median, universe_payload

pytestmark = pytest.mark.browser

LEVELS = ["names", "keys", "all"]
CATCH_ALL = "other"  # domain/classify.OTHER, the last layer of configured layers
LINE_H = 14  # universe.js LINE_H, the height of a line of a table name
Geometry = dict[str, Any]
Opener = Callable[[], Page]


def geometry(p: Page, level: str | None = None) -> Geometry:
    if level:
        p.page.select_option("#u-detail", level)
    return p.page.evaluate("views.universe.geometry()")


def layer_keys(p: Page) -> list[str]:
    return p.page.evaluate("PAGE.universe.layers.map(l => l.key)")


def by_domain(g: Geometry) -> dict[str, list[dict[str, Any]]]:
    out: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for t in g["tables"]:
        out[t["domain"]].append(t)
    return out


def rect(t: dict[str, Any]) -> tuple[float, float, float, float]:
    """The reserved box of a table: (left, top, right, bottom)."""
    cy = t["y"] + t["oy"]
    return t["x"] - t["w"] / 2, cy - t["h"] / 2, t["x"] + t["w"] / 2, cy + t["h"] / 2


def overlapping(boxes: list[tuple[float, float, float, float]]) -> list[tuple[int, int]]:
    """Pairs of strictly overlapping boxes (a sweep along x)."""
    order = sorted(range(len(boxes)), key=lambda j: boxes[j][0])
    found = []
    for a, i in enumerate(order):
        for j in order[a + 1 :]:
            if boxes[j][0] >= boxes[i][2]:
                break
            if boxes[j][1] < boxes[i][3] and boxes[i][1] < boxes[j][3]:
                found.append((i, j))
    return found


@pytest.fixture
def acme(tmp_path: Path, open_page: Any) -> tuple[Path, Opener]:
    """The example page (its satellites folded, D-062) and a way to open it (again)."""
    html, _ = page_of(write_example(tmp_path / "acme_retail"))
    return html, lambda: open_page(html)


@pytest.fixture
def acme_shown(tmp_path: Path, open_page: Any) -> tuple[Path, Opener]:
    """The example page with every table drawn (`universe.fold: false`)."""
    html, _ = page_of(write_example(tmp_path / "acme_retail", fold=False))
    return html, lambda: open_page(html)


@pytest.fixture
def big(tmp_path: Path, open_page: Any) -> tuple[Path, Opener]:
    html = universe_page(tmp_path, universe_payload())
    return html, lambda: open_page(html)


@pytest.fixture(params=["acme", "acme_shown", "big"])
def project(request: pytest.FixtureRequest) -> tuple[Path, Opener]:
    return request.getfixturevalue(request.param)


# ---------------------------------------------------------------- 1. flow order


def assert_layers_left_to_right(g: Geometry, layers: list[str]) -> None:
    ordered = [k for k in layers if not (k == CATCH_ALL and k == layers[-1])]
    for domain, tables in by_domain(g).items():
        present = [k for k in ordered if any(t["layer"] == k for t in tables)]
        for left, right in pairwise(present):
            edge = max(t["x"] + t["w"] / 2 for t in tables if t["layer"] == left)
            start = min(t["x"] - t["w"] / 2 for t in tables if t["layer"] == right)
            assert edge < start, (domain, left, right, edge, start)


def test_layers_run_left_to_right_in_every_domain(project: tuple[Path, Opener]) -> None:
    p = project[1]()
    layers = layer_keys(p)
    for level in LEVELS:
        assert_layers_left_to_right(geometry(p, level), layers)


# acme with layers that leave bronze, silver, seeds and snapshots to the catch-all
PARTIAL_LAYERS = """layers:
  - {key: source, label: Sources, match: ["type:source"]}
  - {key: gold, label: Gold, match: ["path:models/gold/*"]}
"""


def band_of(domain: dict[str, Any], x: float) -> int:
    return next(j for j, b in enumerate(domain["bands"]) if b["x0"] <= x <= b["x1"])


def test_tables_without_a_layer_follow_their_parents(tmp_path: Path, open_page: Any) -> None:
    project = write_example(tmp_path / "acme_retail", fold=False)
    config = (project / "dbt-erd.yml").read_text(encoding="utf-8")
    write_config(project, config[: config.index("layers:")] + PARTIAL_LAYERS + "universe:\n  fold: false\n")
    html, data = page_of(project)
    p = open_page(html)
    nodes = data["universe"]["nodes"]
    assert layer_keys(p)[-1] == CATCH_ALL
    others = {j for j, n in enumerate(nodes) if n["layer"] == CATCH_ALL}
    assert len(others) > 10
    for level in LEVELS:
        g = geometry(p, level)
        assert_layers_left_to_right(g, layer_keys(p))
        domains = {d["key"]: d for d in g["constellations"]}
        at = {t["id"]: t for t in g["tables"]}
        band = {n["id"]: band_of(domains[n["domain"]], at[n["id"]]["x"]) for n in nodes}
        parents: dict[int, list[int]] = defaultdict(list)
        for child, parent in data["universe"]["lineage"]:
            if nodes[child]["domain"] == nodes[parent]["domain"]:
                parents[child].append(parent)
        for j in others:
            uid = nodes[j]["id"]
            if parents[j]:
                assert all(band[uid] >= band[nodes[q]["id"]] for q in parents[j]), (level, nodes[j]["name"])
            else:
                assert band[uid] == 0, (level, nodes[j]["name"])


RANKS = """([members, edges, layers]) => Object.fromEntries(flowRanks(members, edges, i => layers[i]).rank)"""


def test_flow_ranks_place_a_table_without_a_layer_by_lineage(acme: tuple[Path, Opener]) -> None:
    p = acme[1]()

    def ranks(members: list[int], edges: list[list[int]], layers: dict[int, int | None]) -> dict[str, int]:
        return p.page.evaluate(RANKS, [members, edges, {str(k): v for k, v in layers.items()}])

    # 0 -> 1 in layer 0 (span 2), 2 in layer 1; 3 and 4 have no layer (3 reads 0, 4 reads 3), 5 has no parent
    mixed = ranks([0, 1, 2, 3, 4, 5], [[0, 1], [0, 3], [3, 4]], {0: 0, 1: 0, 2: 1, 3: None, 4: None, 5: None})
    assert mixed == {"0": 0, "1": 1, "2": 2, "3": 1, "4": 2, "5": 0}
    alone = ranks([0, 1, 2], [[0, 1]], {0: 0, 1: 0, 2: 1})
    assert {k: mixed[k] for k in alone} == alone  # the spans of the layers are unchanged
    # a chain without a layer longer than layer 0 does not move layer 1's floor
    chain = ranks([0, 1, 2, 3], [[1, 2], [2, 3]], {0: 1, 1: None, 2: None, 3: None})
    assert chain == {"0": 0, "1": 0, "2": 1, "3": 2}


# ---------------------------------------------------------------- 2. no overlap


def test_no_two_reserved_boxes_overlap(project: tuple[Path, Opener]) -> None:
    p = project[1]()
    for level in LEVELS:
        g = geometry(p, level)
        boxes = [rect(t) for t in g["tables"]]
        found = overlapping(boxes)
        assert not found, [(level, g["tables"][i]["id"], g["tables"][j]["id"]) for i, j in found[:5]]


# ---------------------------------------------------------------- 3. names readable

RECORD = r"""() => {
  window.__names = [];
  const draw = CanvasRenderingContext2D.prototype.fillText;
  CanvasRenderingContext2D.prototype.fillText = function (text, x, y, ...rest) {
    if (/\b11px\b/.test(this.font)) window.__names.push([String(text), x, y, this.measureText(text).width]);
    return draw.call(this, text, x, y, ...rest);
  };
}"""


def frame(p: Page, x: float, y: float, k: float) -> None:
    """Centre the world point (x, y) at scale k, through the page's zoom (one draw)."""
    w, h = p.page.evaluate(
        "[document.getElementById('u-stage').clientWidth, document.getElementById('u-stage').clientHeight]"
    )
    p.page.evaluate("t => views.universe.camera(t)", {"x": w / 2 - x * k, "y": h / 2 - y * k, "k": k})


def test_every_name_in_view_is_drawn_at_scale_1(acme: tuple[Path, Opener]) -> None:
    p = acme[1]()
    g = geometry(p, "names")
    p.page.evaluate(RECORD)
    w, h = p.page.evaluate(
        "[document.getElementById('u-stage').clientWidth, document.getElementById('u-stage').clientHeight]"
    )
    for d in g["constellations"]:
        p.page.evaluate("window.__names = []")
        frame(p, d["x"], d["y"], 1)
        cam = p.page.evaluate("views.universe.camera()")
        drawn = p.page.evaluate("window.__names")
        in_view = {
            t["id"].rsplit(".", 1)[1]
            for t in g["tables"]
            if t["domain"] == d["key"] and 0 <= t["x"] + cam["x"] <= w and 0 <= t["y"] + cam["y"] <= h
        }
        labels = label_boxes(drawn)
        names = {text for text, _ in labels}
        shown = len(in_view & names)
        assert shown >= math.floor(len(in_view) * 0.98), (d["key"], sorted(in_view - names))
        assert not overlapping([box for _, box in labels]), d["key"]


def label_boxes(drawn: list[list[Any]]) -> list[tuple[str, tuple[float, float, float, float]]]:
    """The names drawn (fillText calls [text, x, y, width], in order) and their backdrops: the second
    line of a wrapped name follows its first, centred on the same x, 14 px lower (stars are farther apart)."""
    out: list[tuple[str, tuple[float, float, float, float]]] = []
    previous = None
    for text, x, y, m in drawn:
        if previous and previous[1] == x and y == previous[2] + LINE_H and out[-1][0] == previous[0]:
            x0, y0, x1, _ = out[-1][1]
            out[-1] = (previous[0] + text, (min(x0, x - m / 2 - 3), y0, max(x1, x + m / 2 + 3), y + 3))
        else:
            out.append((text, (x - m / 2 - 3, y - 11, x + m / 2 + 3, y + 3)))
        previous = (text, x, y)
    return out


# ---------------------------------------------------------------- 4. circles fit their content

# The fill Σ w·h / (π r²) of every domain of at least 10 tables reaches TARGET, unless the domain is flat:
# its layer bands, left to right, are at least W = Σ (widest box of a band) + gaps wide, so no circle is
# smaller than max(W / 2, √(Σ w·h / π)) + the margin, whatever the packing. A domain below TARGET must
# then be within 15 % of that smallest radius.
# Measured on 2026-11-05: acme 0.237 / 0.134 / 0.170 at names / keys / all (Product, at 1.01 / 1.00 /
# 1.02 of its smallest possible radius; Marketing 0.351 / 0.200 / 0.251), big 0.278 / 0.361 / 0.358.
TARGET = {"names": 0.25, "keys": 0.30, "all": 0.30}
TARGET_BIG = {"names": 0.25, "keys": 0.35, "all": 0.35}
MARGIN = {"names": 16, "keys": 24, "all": 24}  # universe.js margin()
BAND_GAP = 20  # universe.js PACK.BAND_GAP


def smallest_radius(d: dict[str, Any], tables: list[dict[str, Any]]) -> float:
    """A lower bound of the radius of any circle around `tables` in d's left-to-right layer bands."""
    widest = [max(t["w"] for t in tables if b["x0"] <= t["x"] <= b["x1"]) for b in d["bands"]]
    area = sum(t["w"] * t["h"] for t in tables)
    return max((sum(widest) + BAND_GAP * (len(widest) - 1)) / 2, math.sqrt(area / math.pi))


@pytest.mark.parametrize("name", ["acme", "big"])
def test_discs_fit_their_content(name: str, request: pytest.FixtureRequest) -> None:
    p = request.getfixturevalue(name)[1]()
    target = TARGET_BIG if name == "big" else TARGET
    for level in LEVELS:
        g = geometry(p, level)
        tables = by_domain(g)
        for d in g["constellations"]:
            ts = tables[d["key"]]
            for t in ts:
                x0, y0, x1, y1 = rect(t)
                far = math.hypot(
                    max(abs(x0 - d["x"]), abs(x1 - d["x"])), max(abs(y0 - d["y"]), abs(y1 - d["y"]))
                )
                assert far <= d["r"], (level, t["id"])
            if len(ts) >= 10:
                fill = sum(t["w"] * t["h"] for t in ts) / (math.pi * d["r"] ** 2)
                flat = d["r"] <= 1.15 * smallest_radius(d, ts) + MARGIN[level]
                assert fill >= target[level] or flat, (level, d["key"], round(fill, 3))


# ---------------------------------------------------------------- 5. determinism


CARD_RECT = ("x", "y", "w", "h")


def without_time(g: Geometry) -> Geometry:
    """The geometry minus what is not placement: the layout time, and what follows the camera (the summary
    cards' alpha and rectangles: a card has a constant screen size, so its world size follows the zoom)."""
    out = {k: v for k, v in g.items() if k != "layoutMs"}
    out["summary"] = {k: v for k, v in g["summary"].items() if k != "alpha"}
    out["constellations"] = [
        {**c, "summary": {k: v for k, v in c["summary"].items() if k not in CARD_RECT}}
        for c in g["constellations"]
    ]
    return out


def test_two_loads_give_the_same_geometry(acme: tuple[Path, Opener]) -> None:
    first, second = acme[1](), acme[1]()
    for level in LEVELS:
        assert without_time(geometry(first, level)) == without_time(geometry(second, level)), level


def test_a_domain_ticked_off_and_on_comes_back_in_place(acme: tuple[Path, Opener]) -> None:
    p = acme[1]()
    before = without_time(geometry(p))
    box = p.page.locator("#u-domains input").first
    box.click()
    assert without_time(geometry(p)) != before
    box.click()
    assert without_time(geometry(p)) == before


# ---------------------------------------------------------------- 6. saved arrangements

DRAGGED = "stg_erp__orders"
OLD_ACME = {  # a file exported before M5.5: a pinned domain, a table dragged near its domain's centre
    "format": "dbt-erd-layout",
    "version": 1,
    "savedAt": "2026-11-01T09:00:00Z",
    "universe": {
        "keys": {"domains": {"sales": [10, 20]}, "nodes": {"model.acme_retail.stg_erp__orders": [5, -5]}}
    },
}


def assert_saved_layout_wins(g: Geometry, saved: dict[str, Any]) -> None:
    domains = {d["key"]: d for d in g["constellations"]}
    at = {t["id"]: t for t in g["tables"]}
    for key, (x, y) in saved["domains"].items():
        if key in domains:
            assert (domains[key]["x"], domains[key]["y"]) == (x, y), key
    for uid, (dx, dy) in saved["nodes"].items():
        t = at[uid]
        d = domains[t["domain"]]
        assert (t["x"], t["y"]) == pytest.approx((d["x"] + dx, d["y"] + dy), abs=1e-9), uid
        x0, y0, x1, y1 = rect(t)
        assert (
            math.hypot(max(abs(x0 - d["x"]), abs(x1 - d["x"])), max(abs(y0 - d["y"]), abs(y1 - d["y"])))
            <= d["r"]
        )
        hit = [o["id"] for o in g["tables"] if o["id"] != uid and overlapping([rect(t), rect(o)])]
        assert not hit, (uid, hit)


def test_an_arrangement_from_before_m5_5_still_applies(acme: tuple[Path, Opener], tmp_path: Path) -> None:
    p = acme[1]()
    uid = next(t["id"] for t in geometry(p)["tables"] if t["id"].endswith("." + DRAGGED))
    layout = json.loads(json.dumps(OLD_ACME).replace("model.acme_retail.stg_erp__orders", uid))
    old = tmp_path / "dbt-erd-layout.json"
    old.write_text(json.dumps(layout), encoding="utf-8")
    p.page.set_input_files("#l-file", str(old))
    p.page.wait_for_function("!!LAYOUT.get('universe', 'keys')")
    imported = geometry(p, "keys")
    assert_saved_layout_wins(imported, layout["universe"]["keys"])
    # the same arrangement from the browser storage (the import stored it there) gives the same placement
    p.page.reload()
    p.page.wait_for_function("typeof views !== 'undefined' && !!views.universe")
    assert without_time(geometry(p, "keys")) == without_time(imported)


def test_the_edge_reference_layout_still_applies(tmp_path: Path, open_page: Any) -> None:
    html = tmp_path / "edge.html"
    html.write_bytes(reference_page("edge", tmp_path / "edge"))
    p = open_page(html)
    p.page.click("#tabs button[data-tab=universe]")
    p.page.wait_for_function("!!views.universe")
    g = geometry(p, "names")
    saved = EDGE_LAYOUT["universe"]["names"]
    assert SHOP + "dim_customer" in saved["nodes"]
    assert set(saved["domains"]) <= {d["key"] for d in g["constellations"]}  # the pin is checked, not skipped
    assert_saved_layout_wins(g, saved)


# ---------------------------------------------------------------- 7. performance (big, median of 3)

CHANGE = """([id, value]) => {
  const el = document.getElementById(id), t0 = performance.now();
  el.value = value; el.dispatchEvent(new Event('change'));
  return performance.now() - t0;
}"""
UNTICK = """() => { const box = document.querySelector('#u-domains input'), t0 = performance.now();
  box.click(); const took = performance.now() - t0; box.click(); return took; }"""
# the first layout runs in the page's last inline script, before DOMContentLoaded: an upper bound
OPENED = "performance.getEntriesByType('navigation')[0].domContentLoadedEventStart"


def test_big_universe_lays_out_within_budget(big: tuple[Path, Opener]) -> None:
    p = big[1]()
    opened = [p.page.evaluate(OPENED)]
    for _ in range(2):
        p.page.reload()
        p.page.wait_for_function("typeof views !== 'undefined' && !!views.universe")
        opened.append(p.page.evaluate(OPENED))
    changes: dict[str, list[float]] = {"keys": [], "all": [], "untick": []}
    layouts: dict[str, list[float]] = defaultdict(list)
    for _ in range(3):
        for level in ("keys", "all"):
            changes[level].append(p.page.evaluate(CHANGE, ["u-detail", level]))
            layouts[level].append(geometry(p)["layoutMs"])
        p.page.evaluate(CHANGE, ["u-detail", "names"])
        layouts["names"].append(geometry(p)["layoutMs"])
        changes["untick"].append(p.page.evaluate(UNTICK))
    timings = {"open": median(opened), **{k: median(v) for k, v in changes.items()}}
    print("M5.5 big universe timings (ms):", {k: round(v) for k, v in timings.items()}, dict(layouts))
    assert timings["open"] < 3000, timings
    assert all(v < 1000 for k, v in timings.items() if k != "open"), timings
    assert all(median(v) < 1000 for v in layouts.values()), layouts
    assert changes["keys"][0] < 1000 and changes["all"][0] < 1000, changes  # first, uncached


# ---------------------------------------------------------------- 8. layer markers and tooltip

LINES = """() => {
  window.__lines = [];
  const lineTo = CanvasRenderingContext2D.prototype.lineTo;
  CanvasRenderingContext2D.prototype.lineTo = function (x, y) {
    window.__lines.push([x, y]);
    return lineTo.call(this, x, y);
  };
}"""


def markers(d: dict[str, Any]) -> list[tuple[float, float]]:
    """The expected bottom ends of a domain's layer markers (world coordinates)."""
    out = []
    for a, b in pairwise(d["bands"]):
        mx = (a["x1"] + b["x0"]) / 2
        out.append((mx, d["y"] + math.sqrt(d["r"] ** 2 - (mx - d["x"]) ** 2)))
    return out


def test_layer_markers_show_at_constellation_zoom_only(acme: tuple[Path, Opener]) -> None:
    p = acme[1]()
    g = geometry(p)
    d = next(d for d in g["constellations"] if len(d["bands"]) == 4)
    p.page.evaluate(LINES)
    for k, expected in ((1, 3), (0.6, 3), (0.5, 0)):
        p.page.evaluate("window.__lines = []")
        frame(p, d["x"], d["y"], k)
        lines = p.page.evaluate("window.__lines")
        drawn = [
            m for m in markers(d) if any(abs(x - m[0]) < 1e-6 and abs(y - m[1]) < 1e-6 for x, y in lines)
        ]
        assert len(drawn) == expected, (k, d["key"])


HOVER = """([x, y]) => {
  const c = document.getElementById('u-canvas'), r = c.getBoundingClientRect(), t = views.universe.camera();
  const at = { clientX: r.left + x * t.k + t.x, clientY: r.top + y * t.k + t.y, bubbles: true };
  c.dispatchEvent(new MouseEvent('mousemove', at));
  return document.getElementById('u-tip').textContent;
}"""


@pytest.mark.parametrize(("lang", "prefix"), [("en", "Layers: "), ("fr", "Couches\u00a0: ")])
def test_domain_tooltip_lists_its_layers(tmp_path: Path, open_page: Any, lang: str, prefix: str) -> None:
    project = write_example(tmp_path / "acme_retail")
    config = (project / "dbt-erd.yml").read_text(encoding="utf-8")
    write_config(project, config.replace("language: en\n", f"language: {lang}\n"))
    html, data = page_of(project)
    p = open_page(html)
    label = {layer["key"]: layer["label"] for layer in data["universe"]["layers"]}
    g = geometry(p)
    d = next(d for d in g["constellations"] if len(d["bands"]) == 4)
    frame(p, d["x"], d["y"], 1)
    text = p.page.evaluate(HOVER, [d["x"], d["y"] + d["r"] - 4])
    line = prefix + " → ".join(label[b["key"]] for b in d["bands"])
    assert line == "Layers: Sources → Bronze → Silver → Gold".replace("Layers: ", prefix)
    assert line in text, text
    assert re.search(r"\d", text)  # the count line is kept
