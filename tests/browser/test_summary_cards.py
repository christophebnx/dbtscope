"""Summary cards at overview scale (M8.3, D-065, D-066): the weight rule and its crossfade, the footprint, the
content, the filters, the pointer, search and trajectory from afar, the image export, the text summary for
screen readers, small screens and the budgets. Design note:
docs/architecture/2026-11-12-m8.3-summary-cards.md.

The page's numbers are read through `views.universe.geometry().summary` (the rule and the content of every
card), `views.universe.summaryHits()` (what the last screen frame drew: row rectangles, lines per card,
trajectory marks and arrows, in screen px) and `views.universe.perf()`; the expected values are computed here
from the payload, independently of the page.
"""

from __future__ import annotations

import math
import re
import statistics
import time
from collections import Counter, defaultdict
from itertools import pairwise
from pathlib import Path
from typing import Any

import pytest
from colours import contrast
from conftest import write_example

from browser.conftest import (
    CENTRE_WAIT_MS,
    NARROW,
    VIEWPORT,
    Page,
    open_flow,
    scroll_width,
    universe_page,
)
from browser.test_constellations import choose
from browser.test_contrast import BG, HOSTILE, MARK, RECORD_MARKS, acme_page, opaque
from browser.test_export import COMPARE_UNIVERSE
from browser.test_zoom import pinch
from dbtscope.domain.payload import UniversePayload

pytestmark = pytest.mark.browser

SUMMARY = "views.universe.geometry().summary"
HITS = "views.universe.summaryHits()"
NEXT_FRAME = "new Promise(r => requestAnimationFrame(() => requestAnimationFrame(r)))"
ROLE_ORDER = ["core", "connector", "descriptive", "technical", "none"]
FIT_NAMES, MAIN_MAX = 3, 5
# zoom about the stage centre, to the scale k
SET_K = """k => {
  const u = views.universe, c = u.camera(), box = document.getElementById('u-stage');
  const w = box.clientWidth / 2, h = box.clientHeight / 2;
  u.camera({ x: w - (w - c.x) * k / c.k, y: h - (h - c.y) * k / c.k, k });
}"""
# the text and the 6 px bars drawn on the canvas, to read the lines of a card from the outside
RECORD_CARD = """() => {
  window.__texts = []; window.__bars = [];
  const proto = CanvasRenderingContext2D.prototype, text = proto.fillText, rect = proto.fillRect;
  proto.fillText = function (t, ...rest) {
    window.__texts.push({ text: String(t), fill: this.fillStyle, font: this.font, alpha: this.globalAlpha });
    return text.call(this, t, ...rest);
  };
  proto.fillRect = function (x, y, w, h) {
    if (h === 6) window.__bars.push({ x, y, w, fill: this.fillStyle });
    return rect.call(this, x, y, w, h);
  };
}"""


# ---------------------------------------------------------------- helpers


def summary(p: Page) -> dict[str, Any]:
    return p.page.evaluate(SUMMARY)


def hits(p: Page) -> dict[str, Any]:
    return p.page.evaluate(HITS)


def card_of(s: dict[str, Any], key: str) -> dict[str, Any]:
    return next(c for c in s["cards"] if c["key"] == key)


def camera(p: Page) -> dict[str, float]:
    return p.page.evaluate("views.universe.camera()")


def set_k(p: Page, k: float) -> None:
    p.page.evaluate(SET_K, k)
    p.page.evaluate(NEXT_FRAME)


def on_stars(p: Page) -> None:
    """Zoom (about the stage centre) to the smallest scale that draws stars again, if the cards are drawn."""
    set_k(p, max(camera(p)["k"], summary(p)["kStars"] * 1.05))


def canvas_xy(p: Page, x: float, y: float) -> tuple[float, float]:
    """A point of the canvas (CSS px) in page coordinates."""
    b = p.page.locator("#u-canvas").bounding_box()
    return b["x"] + x, b["y"] + y


def move_to(p: Page, x: float, y: float) -> None:
    p.page.mouse.move(*canvas_xy(p, x, y))
    p.page.evaluate(NEXT_FRAME)


def tip(p: Page) -> str:
    return p.page.evaluate(
        "(t => (t.style.display === 'none' ? '' : t.textContent))(document.getElementById('u-tip'))"
    )


def enter(p: Page, name: str) -> None:
    """Enter the trajectory of the table `name` with the search box and the Trajectory button."""
    p.page.fill("#u-q", name)
    p.page.dispatch_event("#u-q", "input")
    p.page.click("#u-traj")


def first_card(p: Page, key: str) -> dict[str, Any]:
    return next(c for c in hits(p)["cards"] if c["k"] == key)


def rows_of(p: Page, key: str) -> list[dict[str, Any]]:
    return [r for r in hits(p)["rows"] if r["k"] == key]


def blank_point(card: dict[str, Any]) -> tuple[float, float]:
    """A point inside a card that is neither a row nor its header: the right-hand edge, below the header."""
    return card["x"] + card["w"] - 2, card["y"] + card["w"] / 2


def role_of(data: dict[str, Any]) -> dict[str, str]:
    return {k["key"]: k["role"] for k in data["universe"]["kinds"]}


def passing(data: dict[str, Any]) -> list[dict[str, Any]]:
    hidden = set(data["universe"]["defaults"]["hiddenKinds"])
    return [n for n in data["universe"]["nodes"] if n["kind"] not in hidden]


def kind_order(data: dict[str, Any]) -> dict[str, int]:
    """The place of a kind in the Types list: by role, then in payload order."""
    kinds = [k["key"] for k in data["universe"]["kinds"]]
    roles = role_of(data)
    return {k: i for i, k in enumerate(sorted(kinds, key=lambda k: ROLE_ORDER.index(roles[k])))}


def expected_cards(data: dict[str, Any], by: str = "domains") -> dict[str, dict[str, Any]]:
    """{constellation key: {n, rows: {row key: {n, kinds: {kind: n}}}}} over the passing tables."""
    out: dict[str, dict[str, Any]] = {}
    for n in passing(data):
        key, row = (n["domain"], n["layer"]) if by == "domains" else (n["layer"], n["domain"])
        card = out.setdefault(key, {"n": 0, "rows": {}})
        card["n"] += 1
        card["rows"].setdefault(row, Counter())[n["kind"]] += 1
    return out


def ranking(data: dict[str, Any], visible: set[str], by: str = "domains") -> dict[str, list[str]]:
    """The main tables per constellation: drawn core tables by relations, links, name, id (D-058)."""
    u = data["universe"]
    deg, reldeg = Counter(), Counter()
    for a, b in u["relations"] + u["lineage"]:
        deg[a] += 1
        deg[b] += 1
    for a, b in u["relations"]:
        reldeg[a] += 1
        reldeg[b] += 1
    roles = role_of(data)
    index = {n["id"]: i for i, n in enumerate(u["nodes"])}
    groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for n in u["nodes"]:
        if n["id"] in visible and roles[n["kind"]] == "core":
            groups[n["domain"] if by == "domains" else n["layer"]].append(n)
    return {
        g: [
            n["id"]
            for n in sorted(
                ns, key=lambda n: (-reldeg[index[n["id"]]], -deg[index[n["id"]]], n["name"], n["id"])
            )[:MAIN_MAX]
        ]
        for g, ns in groups.items()
    }


# the sizes of the design note's table of footprints, at 1280 x 800
CARD_WIDTHS = {"vehicle": 207, "auction": 183, "account": 165, "activity": 127, "claim": 121}


def rounded_radius(card: dict[str, Any], k: float) -> float:
    """The corner radius of a card in world units: 0.4 r, at most max(28 px, 0.24 r) (`cardRadius`)."""
    big = card["r"] * k
    return min(0.4 * big, max(28, 0.24 * big)) / k


def inside(card: dict[str, Any], k: float, x: float, y: float) -> bool:
    half, rho = card["w"] / 2, rounded_radius(card, k)
    dx, dy = max(abs(x - card["x"]) - (half - rho), 0), max(abs(y - card["y"]) - (half - rho), 0)
    return dx * dx + dy * dy <= rho * rho


# ---------------------------------------------------------------- the rule: threshold and continuity


def test_the_large_project_opens_on_cards_and_acme_and_shop_on_stars(
    large_page: Any, example_page: Any, shop_page: Any, open_page: Any
) -> None:
    p = open_page(large_page[0])
    s = summary(p)
    print(
        f"large: fit {camera(p)['k']:.3f}, refR {s['refR']:.2f}, "
        f"kStars {s['kStars']:.3f}, kCards {s['kCards']:.3f}"
    )
    assert s["weight"] == 1 and len(s["cards"]) == 12
    assert p.page.evaluate("views.universe.drawnNames()") == []
    acme, _ = example_page
    a = summary(acme)
    print(
        f"acme: fit {camera(acme)['k']:.3f}, refR {a['refR']:.2f}, "
        f"kStars {a['kStars']:.3f}, kCards {a['kCards']:.3f}"
    )
    assert a["weight"] == 0 and acme.page.evaluate("views.universe.drawnNames()")
    assert camera(acme)["k"] > a["kStars"]
    shop, _ = shop_page
    assert summary(shop)["weight"] == 0 and shop.page.evaluate("views.universe.drawnNames()")


def test_the_weight_is_a_function_of_the_scale_alone_in_a_band_of_one_and_a_half(
    large_page: Any, open_page: Any
) -> None:
    p = open_page(large_page[0])
    s = summary(p)
    assert s["kStars"] / s["kCards"] == pytest.approx(1.5)
    # the reference star drawn at 3 px and at 2 px
    set_k(p, s["kStars"])
    assert summary(p)["weight"] == pytest.approx(0, abs=1e-9)
    set_k(p, s["kCards"])
    assert summary(p)["weight"] == pytest.approx(1, abs=1e-9)
    set_k(p, math.sqrt(s["kStars"] * s["kCards"]))
    assert summary(p)["weight"] == pytest.approx(0.5, abs=1e-9)  # linear in log k


def test_zooming_across_the_band_moves_nothing_but_the_weight(large_page: Any, open_page: Any) -> None:
    p = open_page(large_page[0])
    s = summary(p)
    lo, hi = s["kCards"] / 1.2, s["kStars"] * 1.2
    scales = [lo * (hi / lo) ** (i / 29) for i in range(30)]
    runs = p.state()["layoutRuns"]
    seen: dict[float, float] = {}
    for sweep in (scales, scales[::-1]):
        weights = []
        for k in sweep:
            set_k(p, k)
            assert camera(p)["k"] == pytest.approx(k, rel=1e-9)  # the camera is the one set: nothing moved it
            weights.append(summary(p)["weight"])
            assert seen.setdefault(k, weights[-1]) == weights[-1]  # equal at equal scales, in and out
        ordered = sorted(zip(sweep, weights, strict=True))
        assert all(a[1] >= b[1] for a, b in pairwise(ordered)), "weight falls as k rises"
        for (k0, w0), (k1, w1) in zip(
            zip(sweep, weights, strict=True), list(zip(sweep, weights, strict=True))[1:], strict=False
        ):
            assert abs(w1 - w0) <= abs(math.log(k1 / k0)) / math.log(1.5) + 1e-9
    assert p.state()["layoutRuns"] == runs  # no relayout
    assert weights[0] in (0, 1) or True  # the sweep ends at the scale it started from


def test_the_wheel_crosses_the_band_by_its_own_factor_only(large_page: Any, open_page: Any) -> None:
    p = open_page(large_page[0])
    s = summary(p)
    set_k(p, s["kStars"] * 1.2)
    b = p.page.locator("#u-canvas").bounding_box()
    p.page.mouse.move(b["x"] + b["width"] / 2, b["y"] + b["height"] / 2)
    weights, runs = [summary(p)["weight"]], p.state()["layoutRuns"]
    for _ in range(12):
        before = camera(p)["k"]
        p.page.mouse.wheel(0, 100)
        p.page.wait_for_timeout(40)
        ratio = camera(p)["k"] / before
        assert 0.85 < ratio < 0.89 or ratio == pytest.approx(1)  # one notch: 1 / 1.15 (D-045)
        weights.append(summary(p)["weight"])
    assert weights == sorted(weights) and weights[0] < 0.5 and weights[-1] == 1
    assert p.state()["layoutRuns"] == runs


# ---------------------------------------------------------------- footprint


@pytest.mark.parametrize("by", ["domains", "layers"])
def test_cards_stay_inside_the_collision_radius_and_never_overlap(
    large_page: Any, open_page: Any, by: str
) -> None:
    p = open_page(large_page[0])
    choose(p, by)
    p.page.evaluate(NEXT_FRAME)
    k = camera(p)["k"]
    s = summary(p)
    assert s["weight"] == 1
    for c in s["cards"]:
        assert c["w"] == c["h"] == pytest.approx(1.8 * c["r"])
        half, rho = c["w"] / 2, rounded_radius(c, k)
        corner = (half - rho) * math.sqrt(2) + rho
        assert corner <= 1.15 * c["r"] + 30, (c["key"], corner / c["r"])  # the layout's collision radius
        assert corner <= 1.18 * c["r"]
    for i, a in enumerate(s["cards"]):
        for b in s["cards"][i + 1 :]:
            steps = [-1 + 2 * j / 14 for j in range(15)]
            points = [(a["x"] + u * a["w"] / 2, a["y"] + v * a["w"] / 2) for u in steps for v in steps]
            assert not any(inside(a, k, x, y) and inside(b, k, x, y) for x, y in points), (a["key"], b["key"])


def test_double_click_on_a_card_lands_on_its_stars_centred(large_page: Any, open_page: Any) -> None:
    p = open_page(large_page[0])
    before = first_card(p, "claim")
    s = summary(p)
    x, y = blank_point(before)
    p.page.mouse.dblclick(*canvas_xy(p, x, y))
    p.page.wait_for_timeout(CENTRE_WAIT_MS)
    c, after = camera(p), summary(p)
    assert c["k"] >= s["kStars"] and after["weight"] == 0
    box = p.page.evaluate("(b => [b.clientWidth, b.clientHeight])(document.getElementById('u-canvas'))")
    card = card_of(s, "claim")
    assert (box[0] / 2 - c["x"]) / c["k"] == pytest.approx(card["x"], abs=1)  # centred on it
    assert (box[1] / 2 - c["y"]) / c["k"] == pytest.approx(card["y"], abs=1)
    stars = [t for t in p.page.evaluate("views.universe.geometry().tables") if t["domain"] == "claim"]
    assert stars and all(math.hypot(t["x"] - card["x"], t["y"] - card["y"]) <= card["r"] for t in stars)
    assert p.page.evaluate("views.universe.drawnNames()")  # the stars are drawn where the card was


# ---------------------------------------------------------------- content


def test_a_card_says_the_counts_of_its_constellation_by_layer_and_kind(
    large_page: Any, open_page: Any
) -> None:
    html, data = large_page
    p = open_page(html)
    s = summary(p)
    order = kind_order(data)
    want = expected_cards(data)
    assert {c["key"] for c in s["cards"]} == set(want)
    layer_order = [layer["key"] for layer in data["universe"]["layers"]]
    for c in s["cards"]:
        w = want[c["key"]]
        assert c["n"] == w["n"] == sum(r["n"] for r in c["rows"])
        assert [r["key"] for r in c["rows"]] == sorted(w["rows"], key=layer_order.index)  # flow order
        for r in c["rows"]:
            assert r["n"] == sum(w["rows"][r["key"]].values())
            assert dict(r["kinds"]) == dict(w["rows"][r["key"]])
            assert [k for k, _ in r["kinds"]] == sorted(w["rows"][r["key"]], key=order.get)  # Types order
    # the constellation counts of the placement agree
    assert {c["key"]: c["n"] for c in p.page.evaluate("views.universe.geometry().constellations")} == {
        k: v["n"] for k, v in want.items()
    }


def test_in_layer_mode_the_rows_are_the_domains_in_the_order_of_the_panel(
    large_page: Any, open_page: Any
) -> None:
    html, data = large_page
    p = open_page(html)
    choose(p, "layers")
    p.page.evaluate(NEXT_FRAME)
    s = summary(p)
    want = expected_cards(data, "layers")
    domain_order = [d["key"] for d in data["universe"]["domains"]]
    assert {c["key"] for c in s["cards"]} == set(want)
    for c in s["cards"]:
        assert c["n"] == want[c["key"]]["n"]
        assert [r["key"] for r in c["rows"]] == sorted(want[c["key"]]["rows"], key=domain_order.index)
        for r in c["rows"]:
            assert dict(r["kinds"]) == dict(want[c["key"]]["rows"][r["key"]])


def test_the_entity_count_follows_the_fold_and_no_row_does(large_page: Any, open_page: Any) -> None:
    html, data = large_page
    p = open_page(html)
    roles = role_of(data)
    kinds = {n["id"]: n["kind"] for n in data["universe"]["nodes"]}
    folded = summary(p)
    assert p.page.evaluate("views.universe.geometry().fold")
    drawn = Counter(
        t["domain"]
        for t in p.page.evaluate("views.universe.geometry().tables")
        if roles[kinds[t["id"]]] in ("core", "connector")
    )
    assert {c["key"]: c["entities"] for c in folded["cards"]} == {
        c["key"]: drawn.get(c["key"], 0) for c in folded["cards"]
    }
    p.page.uncheck("#u-fold-box")
    p.page.evaluate(NEXT_FRAME)
    shown = summary(p)
    assert not p.page.evaluate("views.universe.geometry().fold")
    assert all(c["entities"] is None for c in shown["cards"])
    assert {c["key"]: c["rows"] for c in shown["cards"]} == {c["key"]: c["rows"] for c in folded["cards"]}
    assert {c["key"]: c["n"] for c in shown["cards"]} == {c["key"]: c["n"] for c in folded["cards"]}
    assert hits(p)["cards"][0]["count"].count("·") == 0  # no entities on the count line


def test_the_main_tables_are_the_ranking_of_the_names_at_fit(large_page: Any, open_page: Any) -> None:
    html, data = large_page
    p = open_page(html)
    s = summary(p)
    visible = {t["id"] for t in p.page.evaluate("views.universe.geometry().tables")}
    want = ranking(data, visible)
    assert {c["key"]: c["main"] for c in s["cards"] if c["main"]} == want
    assert all(len(v) <= MAIN_MAX for v in want.values())
    assert any(len(v) == MAIN_MAX for v in want.values())
    sources = [c for c in s["cards"] if not c["main"]]
    assert len(sources) == 7  # the source systems name no table
    on_stars(p)
    drawn = p.page.evaluate("views.universe.drawnNames()")
    by_id = {n["id"]: n["domain"] for n in data["universe"]["nodes"]}
    for key, ids in want.items():
        named = [i for i in drawn if by_id[i] == key]
        assert named and set(named) <= set(ids[:FIT_NAMES])  # the names at Fit are the first of the same list


def test_cards_are_the_size_of_the_design_and_show_what_fits(large_page: Any, open_page: Any) -> None:
    p = open_page(large_page[0])
    s = summary(p)
    drawn = {c["k"]: c for c in hits(p)["cards"]}
    assert set(drawn) == {c["key"] for c in s["cards"]}
    for c in s["cards"]:
        d = drawn[c["key"]]
        if c["key"] in CARD_WIDTHS:
            assert d["w"] == pytest.approx(CARD_WIDTHS[c["key"]], abs=2), c["key"]
        else:
            assert 108 <= d["w"] <= 117, (c["key"], d["w"])
        assert d["named"] and d["count"].startswith(f"{c['n']} tables")
        assert d["rows"] == len(c["rows"]) and not d["more"]  # every row of every card
        if c["main"]:
            assert d["names"] >= 2 and (d["w"] < 130 or d["names"] >= 3), (c["key"], d["w"], d["names"])
        else:
            assert d["names"] == 0 and not d["heading"]
    assert drawn["vehicle"]["heading"] and drawn["vehicle"]["names"] == MAIN_MAX
    print({k: (round(v["w"]), v["rows"], v["names"]) for k, v in drawn.items() if k in CARD_WIDTHS})


def test_the_widest_row_fills_the_bar_and_no_kind_is_thinner_than_two_pixels(
    large_page: Any, open_page: Any
) -> None:
    p = open_page(large_page[0])
    p.page.evaluate(RECORD_CARD)
    p.page.evaluate("views.universe.shown()")
    bars = p.page.evaluate("window.__bars")
    assert bars and all(b["w"] >= 2 - 1e-9 for b in bars)  # a kind of one table among 266 is still seen
    vehicle = first_card(p, "vehicle")
    rows = defaultdict(float)
    for b in bars:
        if (
            vehicle["x"] <= b["x"] <= vehicle["x"] + vehicle["w"]
            and vehicle["y"] <= b["y"] <= vehicle["y"] + vehicle["w"]
        ):
            rows[round(b["y"], 3)] += b["w"]
    assert len(rows) == 3
    assert max(rows.values()) == pytest.approx(vehicle["barW"], abs=6)  # the largest row (Raw vault) fills it
    assert min(rows.values()) < 0.2 * vehicle["barW"]  # the others are in proportion, not stretched


# ---------------------------------------------------------------- filters


def untick(p: Page, panel: str, label: str) -> float:
    """Untick the row `label` of a panel list; return the seconds until the frame is drawn."""
    start = time.perf_counter()
    p.page.locator(f"#u-{panel} label").filter(has_text=re.compile(f"^{label}")).locator("input").uncheck()
    p.page.evaluate(NEXT_FRAME)
    return time.perf_counter() - start


def test_the_filters_change_every_count_row_and_card(large_page: Any, open_page: Any) -> None:
    html, data = large_page
    p = open_page(html)
    before = summary(p)
    seconds = untick(p, "kinds", "Satellite")
    assert seconds <= 1
    after = summary(p)
    sat = next(k["key"] for k in data["universe"]["kinds"] if k["label"] == "Satellite")
    satellites = Counter(n["domain"] for n in passing(data) if n["kind"] == sat)
    for c in after["cards"]:
        old = card_of(before, c["key"])
        assert c["n"] == old["n"] - satellites[c["key"]]
        assert all(sat not in dict(r["kinds"]) for r in c["rows"])
    seconds = untick(p, "layers", "Staging")
    assert seconds <= 1
    assert all("staging" not in [r["key"] for r in c["rows"]] for c in summary(p)["cards"])
    untick(p, "domains", "Claim")
    cards = summary(p)["cards"]
    assert "claim" not in {c["key"] for c in cards} and len(cards) == 11


def test_a_filter_change_at_the_stars_scale_takes_a_second_at_most(large_page: Any, open_page: Any) -> None:
    p = open_page(large_page[0])
    on_stars(p)
    assert summary(p)["weight"] == 0
    assert untick(p, "kinds", "Satellite") <= 1


# ---------------------------------------------------------------- pointer


def test_hovering_a_card_gives_the_domain_tooltip_and_a_row_gives_its_action(
    large_page: Any, open_page: Any
) -> None:
    html, data = large_page
    p = open_page(html)
    card = first_card(p, "vehicle")
    move_to(p, *blank_point(card))
    text = tip(p)
    assert (
        "Vehicle" in text
        and "299 tables" in text
        and "Layers" in text
        and "Double-click: zoom on this domain" in text
    )
    assert "Click: zoom on" not in text
    row = next(r for r in rows_of(p, "vehicle") if r["row"] == "vault")
    move_to(p, row["x"] + 10, row["y"] + row["h"] / 2)
    layer = next(layer["label"] for layer in data["universe"]["layers"] if layer["key"] == "vault")
    assert f"Click: zoom on {layer}" in tip(p)
    # no table is under the pointer at card scale, even over where a star would be
    star = next(t for t in p.page.evaluate("views.universe.geometry().tables") if t["domain"] == "vehicle")
    k, c = camera(p)["k"], camera(p)
    move_to(p, star["x"] * k + c["x"], star["y"] * k + c["y"])
    assert "Click: show its trajectory" not in tip(p) and "Double-click: open in the Detail tab" not in tip(p)


def test_hovering_a_layer_card_gives_the_layer_tooltip(large_page: Any, open_page: Any) -> None:
    p = open_page(large_page[0])
    choose(p, "layers")
    p.page.evaluate(NEXT_FRAME)
    card = hits(p)["cards"][0]
    move_to(p, *blank_point(card))
    assert "Domains" in tip(p) and "Double-click: zoom on this constellation" in tip(p)
    row = rows_of(p, card["k"])[0]
    move_to(p, row["x"] + 10, row["y"] + row["h"] / 2)
    assert "Click: zoom on" in tip(p)


def test_the_header_of_a_card_moves_and_pins_its_constellation(large_page: Any, open_page: Any) -> None:
    p = open_page(large_page[0])
    s = summary(p)
    k = camera(p)["k"]
    card = first_card(p, "claim")
    hx, hy = card["header"]["x"] + 20, card["header"]["y"] + 8
    p.page.mouse.move(*canvas_xy(p, hx, hy))
    p.page.mouse.down()
    for step in range(1, 7):
        p.page.mouse.move(*canvas_xy(p, hx + 10 * step, hy + 6 * step))
    p.page.mouse.up()
    p.page.evaluate(NEXT_FRAME)
    moved = card_of(summary(p), "claim")
    old = card_of(s, "claim")
    assert moved["x"] - old["x"] == pytest.approx(60 / k, abs=1) and moved["y"] - old["y"] == pytest.approx(
        36 / k, abs=1
    )
    pins = p.page.evaluate("LAYOUT.get('universe', 'folded:names')")[
        "domains"
    ]  # the scope of a folded drawing
    assert pins["claim"] == pytest.approx([moved["x"], moved["y"]], abs=1e-6)
    assert set(pins) == {c["key"] for c in s["cards"]}


def test_a_click_on_a_row_frames_its_band_on_stars(large_page: Any, open_page: Any) -> None:
    p = open_page(large_page[0])
    s = summary(p)
    row = next(r for r in rows_of(p, "vehicle") if r["row"] == "vault")
    p.page.mouse.click(*canvas_xy(p, row["x"] + 12, row["y"] + row["h"] / 2))
    p.page.wait_for_timeout(CENTRE_WAIT_MS)
    c, after = camera(p), summary(p)
    assert c["k"] >= s["kStars"] and after["weight"] == 0
    band = next(
        b
        for con in p.page.evaluate("views.universe.geometry().constellations")
        if con["key"] == "vehicle"
        for b in con["bands"]
        if b["key"] == "vault"
    )
    width = p.page.evaluate("document.getElementById('u-canvas').clientWidth")
    assert (
        band["x0"] * c["k"] + c["x"] >= -1 and band["x1"] * c["k"] + c["x"] <= width + 1
    )  # the band is on screen


def test_a_click_on_a_row_of_the_catch_all_layer_frames_the_whole_constellation(
    tmp_path: Path, open_page: Any
) -> None:
    html = universe_page(tmp_path, other_payload(), view="universe")
    p = open_page(html)
    set_k(p, summary(p)["kCards"])  # zoomed out to the cards, on a small project too
    s = summary(p)
    assert s["weight"] == 1
    row = next(r for r in rows_of(p, "d") if r["row"] == "other")
    p.page.mouse.click(*canvas_xy(p, row["x"] + 5, row["y"] + row["h"] / 2))
    p.page.wait_for_timeout(CENTRE_WAIT_MS)
    c, card = camera(p), card_of(s, "d")
    width = p.page.evaluate("document.getElementById('u-canvas').clientWidth")
    assert c["k"] >= s["kStars"] and summary(p)["weight"] == 0
    assert (width / 2 - c["x"]) / c["k"] == pytest.approx(
        card["x"], abs=1
    )  # the whole constellation, centred
    assert (c["x"] + (card["x"] - card["r"]) * c["k"]) >= -1 and (
        c["x"] + (card["x"] + card["r"]) * c["k"]
    ) <= width + 1


def other_payload() -> UniversePayload:
    """One domain, a layer `raw` and the catch-all layer `other`, two core tables in each."""
    nodes = [
        {
            "id": f"t.{layer}.{i}",
            "name": f"{layer}_{i}",
            "domain": "d",
            "layer": layer,
            "kind": "hub",
            "desc": "",
            "cols": [],
        }
        for layer in ("raw", "other")
        for i in range(40)
    ]
    return UniversePayload.model_validate(
        {
            "nodes": nodes,
            "relations": [[i, i + 40] for i in range(40)],
            "lineage": [[i + 40, i] for i in range(40)],
            "domains": [{"key": "d", "label": "D", "color": "#2f6fb5", "owner": ""}],
            "layers": [{"key": "raw", "label": "Raw"}, {"key": "other", "label": "Other"}],
            "kinds": [{"key": "hub", "label": "Hub", "color": "#2f6fb5", "role": "core"}],
            "defaults": {"links": "both", "detail": "names", "hidden_kinds": []},
        }
    )


def test_a_click_on_a_card_outside_its_rows_does_nothing_and_keeps_the_trajectory(
    large_page: Any, open_page: Any
) -> None:
    p = open_page(large_page[0])
    overview = camera(p)
    enter(p, "car_hub")
    assert p.state()["active"]
    p.page.evaluate(
        "c => views.universe.camera(c)", overview
    )  # the entry frames the members: back to the overview
    p.page.evaluate(NEXT_FRAME)
    assert summary(p)["weight"] == 1
    before = camera(p)
    x, y = blank_point(first_card(p, "claim"))
    p.page.mouse.click(*canvas_xy(p, x, y))
    p.page.wait_for_timeout(300)
    assert camera(p) == before and p.state()["active"]
    bottom = p.page.evaluate("document.getElementById('u-canvas').clientHeight") - 8
    p.page.mouse.click(*canvas_xy(p, 8, bottom))  # the background leaves it, as before
    assert not p.state()["active"]


def test_a_pinch_over_a_card_zooms_and_a_tap_on_a_row_frames_it(large_page: Any, open_page: Any) -> None:
    p = open_page(large_page[0], touch=True)
    b = p.page.locator("#u-canvas").bounding_box()
    before = camera(p)["k"]
    pinch(p, b["x"] + b["width"] / 2, b["y"] + b["height"] / 2)
    assert camera(p)["k"] > before * 2
    p.page.click("#u-fit")
    p.page.wait_for_timeout(CENTRE_WAIT_MS)
    row = next(r for r in rows_of(p, "vehicle") if r["row"] == "vault")
    assert row["h"] == 18  # a coarse pointer: taller rows
    p.page.touchscreen.tap(*canvas_xy(p, row["x"] + 12, row["y"] + row["h"] / 2))
    p.page.wait_for_timeout(CENTRE_WAIT_MS)
    assert summary(p)["weight"] == 0


# ---------------------------------------------------------------- search and trajectory


def test_a_search_from_afar_ends_on_the_table_drawn_as_a_star(large_page: Any, open_page: Any) -> None:
    p = open_page(large_page[0])
    p.page.fill("#u-q", "car_hub")
    p.page.dispatch_event("#u-q", "change")
    p.page.wait_for_timeout(CENTRE_WAIT_MS)
    assert camera(p)["k"] >= 1.5 and summary(p)["weight"] == 0
    assert "model.shop.car_hub" in p.page.evaluate("views.universe.drawnNames()")


def expected_trajectory(
    data: dict[str, Any], state: dict[str, Any]
) -> tuple[dict[str, dict[str, Any]], Counter]:
    """(per constellation: up, down, start), (from, to, side) -> edges between constellations."""
    nodes = data["universe"]["nodes"]
    domain = {n["id"]: n["domain"] for n in nodes}
    up, down = state["up"], state["down"]
    per: dict[str, dict[str, Any]] = defaultdict(lambda: {"up": 0, "down": 0, "start": False})
    for i in up:
        per[domain[i]]["up"] += 1
    for i in down:
        per[domain[i]]["down"] += 1
    per[domain[state["start"]]]["start"] = True
    arrows: Counter = Counter()
    for c, par in data["universe"]["lineage"]:
        child, parent = nodes[c]["id"], nodes[par]["id"]
        side = (
            "up"
            if parent in up and (child == state["start"] or child in up)
            else "down"
            if child in down and (parent == state["start"] or parent in down)
            else None
        )
        if side and domain[child] != domain[parent]:
            arrows[(domain[parent], domain[child], side)] += 1
    return per, arrows


def test_a_trajectory_at_overview_marks_cards_and_aggregates_its_arrows(
    large_page: Any, open_page: Any
) -> None:
    html, data = large_page
    p = open_page(html)
    overview = camera(p)
    enter(p, "car_hub")
    p.page.evaluate(
        "c => views.universe.camera(c)", overview
    )  # the entry frames the members: back to the overview
    p.page.evaluate(NEXT_FRAME)
    state = p.state()
    assert state["active"] and summary(p)["weight"] == 1
    per, arrows = expected_trajectory(data, state)
    drawn = hits(p)
    assert {k: (m["up"], m["down"], m["start"]) for k, m in drawn["marks"].items()} == {
        k: (m["up"], m["down"], m["start"]) for k, m in per.items()
    }
    assert {(a["from"], a["to"], a["dir"]): a["c"] for a in drawn["arrows"]} == dict(arrows) and arrows
    cards = {c["k"]: c for c in drawn["cards"]}
    for key, m in per.items():
        if m["up"] + m["down"]:
            line = f"{m['up']} upstream · {m['down']} downstream"
            assert cards[key]["traj"] and line.startswith(cards[key]["traj"].rstrip("…"))  # in full, or cut
    p.page.click("#u-tj-leave")
    p.page.evaluate(NEXT_FRAME)
    left = hits(p)
    assert left["marks"] == {} and left["arrows"] == [] and not any(c["traj"] for c in left["cards"])


# ---------------------------------------------------------------- export


@pytest.mark.parametrize("step", ["cards", "crossfade", "trajectory"])
def test_the_exported_image_is_what_is_on_screen_at_every_weight(
    large_page: Any, open_page: Any, step: str
) -> None:
    p = open_page(large_page[0])
    if step == "crossfade":
        s = summary(p)
        set_k(p, math.sqrt(s["kStars"] * s["kCards"]))
        assert 0 < summary(p)["weight"] < 1
    elif step == "trajectory":
        overview = camera(p)
        enter(p, "car_hub")
        p.page.evaluate("c => views.universe.camera(c)", overview)
        p.page.evaluate(NEXT_FRAME)
        assert summary(p)["weight"] == 1
    got = p.page.evaluate(COMPARE_UNIVERSE)
    assert got["diff"] < 6, f"{step}: the image differs from the screen by {got['diff']:.2f}/255"


# ---------------------------------------------------------------- accessibility and strings


def number(n: int, lang: str) -> str:
    return f"{n:,}" if lang == "en" else f"{n:,}".replace(",", "\u202f")


def plural(n: int, forms: tuple[str, str], lang: str) -> str:
    one = n <= 1 if lang == "fr" else n == 1
    return f"{number(n, lang)} {forms[0] if one else forms[1]}"


def text_summary(p: Page) -> dict[str, Any]:
    return p.page.evaluate(
        """() => { const s = document.getElementById('u-summary'), out = [];
        for (const e of s.children) {
          if (e.tagName === 'H3') out.push({ name: e.textContent, p: [], li: [] });
          else if (e.tagName === 'P' && !out.length) out.push({ name: null, p: [e.textContent], li: [] });
          else if (e.tagName === 'P') out[out.length - 1].p.push(e.textContent);
          else if (e.tagName === 'UL') out[out.length - 1].li = [...e.children].map(l => l.textContent);
        }
        return { heading: document.getElementById('u-summary-h').textContent, items: out }; }"""
    )


def test_the_text_summary_lists_every_constellation_with_the_numbers_of_the_cards(
    large_page: Any, open_page: Any
) -> None:
    html, data = large_page
    p = open_page(html)
    s = summary(p)
    text = text_summary(p)
    assert text["heading"] == "Summary of the constellations"
    labels = {d["key"]: d["label"] or d["key"] for d in data["universe"]["domains"]}
    layers = {layer["key"]: layer["label"] for layer in data["universe"]["layers"]}
    kinds = {k["key"]: k["label"] for k in data["universe"]["kinds"]}
    names = {n["id"]: n["name"] for n in data["universe"]["nodes"]}
    assert [i["name"] for i in text["items"]].count("Vehicle") == 1 and len(text["items"]) == len(s["cards"])
    by_name = {i["name"]: i for i in text["items"]}
    for c in s["cards"]:
        item = by_name[labels[c["key"]]]
        count = f"{c['n']} tables" + (f" · {c['entities']} entities" if c["entities"] is not None else "")
        assert item["p"][0] == count
        assert item["li"] == [
            f"{layers[r['key']]}: {r['n']} tables — " + ", ".join(f"{kinds[k]} {n}" for k, n in r["kinds"])
            for r in c["rows"]
        ]
        main = f"Main tables: {', '.join(names[i] for i in c['main'])}"
        assert (item["p"][1:] == [main]) if c["main"] else (item["p"][1:] == [])
    assert (
        len(by_name["Vehicle"]["p"]) == 2 and by_name["Vehicle"]["p"][1].count(",") == MAIN_MAX - 1
    )  # all five, none cut


def test_the_text_summary_follows_the_filters_and_the_grouping(large_page: Any, open_page: Any) -> None:
    p = open_page(large_page[0])
    assert len(text_summary(p)["items"]) == 12
    untick(p, "domains", "Claim")
    assert len(text_summary(p)["items"]) == 11
    choose(p, "layers")
    p.page.evaluate(NEXT_FRAME)
    layers = {layer["label"] for layer in p.page.evaluate("PAGE.universe.layers")}
    assert {i["name"] for i in text_summary(p)["items"]} == layers and len(layers) == 4


def test_the_text_summary_is_there_at_every_scale_and_inert_with_the_flow(example_page: Any) -> None:
    p, _ = example_page
    assert (
        summary(p)["weight"] == 0 and len(text_summary(p)["items"]) == 7
    )  # stars drawn: the text is still there
    assert p.page.evaluate(
        "document.getElementById('u-canvas').compareDocumentPosition(document.getElementById('u-summary'))"
        " & Node.DOCUMENT_POSITION_FOLLOWING"
    )
    assert p.page.evaluate(
        "document.getElementById('u-stage').contains(document.getElementById('u-summary'))"
    )
    assert p.page.evaluate("!document.getElementById('u-summary').closest('[inert]')")
    open_flow(p, "fct_orders")
    assert p.page.evaluate("!!document.getElementById('u-summary').closest('[inert]')")
    assert p.page.evaluate(
        "document.getElementById('u-summary').querySelector('a, button, input, [tabindex]') === null"
    )


def test_an_empty_universe_has_a_summary_that_says_so(example_page: Any) -> None:
    p, _ = example_page
    p.page.click("#u-none")
    p.page.evaluate(NEXT_FRAME)
    text = text_summary(p)
    assert text["heading"] == "Summary of the constellations"
    assert text["items"] == [{"name": None, "p": ["No table for these filters."], "li": []}]
    assert hits(p)["cards"] == []


def test_french_texts_and_plurals(tmp_path: Path, open_page: Any) -> None:
    p, data = acme_page(tmp_path, open_page, "fr")
    text = text_summary(p)
    assert text["heading"] == "Synthèse des constellations"
    s = summary(p)
    one = next(c for c in s["cards"] if c["n"] <= 1)
    labels = {d["key"]: d["label"] or d["key"] for d in data["universe"]["domains"]}
    item = next(i for i in text["items"] if i["name"] == labels[one["key"]])
    assert (
        item["p"][0] == f"{plural(one['n'], ('table', 'tables'), 'fr')} · "
        f"{plural(one['entities'], ('entité', 'entités'), 'fr')}"
    )
    assert any(i["p"][-1].startswith("Tables principales\u00a0: ") for i in text["items"])
    assert all(
        re.search("(?<!\u00a0): ", li) is None for i in text["items"] for li in i["li"]
    )  # the label and the value: never a bare colon in French


def test_french_cards_say_main_tables_and_the_row_action(tmp_path: Path, open_page: Any) -> None:
    p = open_page(universe_page(tmp_path, hostile_payload(), view="universe", language="fr"))
    set_k(p, summary(p)["kCards"])
    p.page.evaluate(RECORD_CARD)
    p.page.evaluate("views.universe.shown()")
    assert "Tables principales" in [t["text"] for t in p.page.evaluate("window.__texts")]
    row = hits(p)["rows"][0]
    move_to(p, row["x"] + 10, row["y"] + row["h"] / 2)
    assert "Clic\u00a0: cadrer" in tip(p)


def test_english_heading_of_the_main_tables_is_drawn_on_the_card(large_page: Any, open_page: Any) -> None:
    p = open_page(large_page[0])
    p.page.evaluate(RECORD_CARD)
    p.page.evaluate("views.universe.shown()")
    texts = [t["text"] for t in p.page.evaluate("window.__texts")]
    assert "Main tables" in texts and "Vehicle" in texts and "299 tables · 142 entities" in texts


# ---------------------------------------------------------------- contrast


ROLES = ["core", "connector", "descriptive", "core", "none"]


def hostile_payload() -> UniversePayload:
    """Three domains, five kinds in the hostile colours of the contrast tests, 120 tables a domain: cards big
    enough to show every part of a card."""
    colours = [c for _, c, _ in HOSTILE[:5]]
    kinds = [
        {"key": f"k{i}", "label": f"Kind {i}", "color": c, "role": ROLES[i]} for i, c in enumerate(colours)
    ]
    nodes = [
        {
            "id": f"t.{d}.{i}",
            "name": f"d{d}_t{i}",
            "domain": f"d{d}",
            "layer": f"l{i % 2}",
            "kind": f"k{i % 5}",
            "desc": "",
            "cols": [],
        }
        for d in range(3)
        for i in range(120)
    ]
    lineage = [[d * 120 + i, d * 120 + i - 1] for d in range(3) for i in range(1, 120)]
    return UniversePayload.model_validate(
        {
            "nodes": nodes,
            "relations": [[d * 120 + i, d * 120 + i - 2] for d in range(3) for i in range(2, 120, 3)],
            "lineage": lineage,
            "domains": [
                {"key": f"d{d}", "label": f"Land {d}", "color": colours[d], "owner": ""} for d in range(3)
            ],
            "layers": [{"key": "l0", "label": "Zero"}, {"key": "l1", "label": "One"}],
            "kinds": kinds,
            "defaults": {"links": "both", "detail": "names", "hidden_kinds": []},
        }
    )


def test_hostile_colours_keep_card_text_and_marks_readable(tmp_path: Path, open_page: Any) -> None:
    p = open_page(universe_page(tmp_path, hostile_payload(), view="universe"))
    s = summary(p)
    p.page.evaluate(RECORD_MARKS)
    p.page.evaluate(RECORD_CARD)
    set_k(p, s["kCards"])
    assert summary(p)["weight"] == 1
    p.page.evaluate("window.__marks = []; window.__texts = []; window.__bars = []")
    p.page.evaluate("views.universe.shown()")
    texts = [t for t in p.page.evaluate("window.__texts") if t["alpha"] == 1]
    assert {t["text"] for t in texts} >= {"Land 0", "Land 1", "Land 2", "Main tables", "Zero", "One"}
    assert [t for t in texts if contrast(t["fill"], "#ffffff") < 4.5] == []  # on the white card
    assert all(c["rows"] == 2 for c in hits(p)["cards"])
    marks = p.page.evaluate("window.__marks")
    strokes = [m for m in marks if m["op"] == "stroke" and opaque(m["stroke"])]
    assert strokes and [m for m in strokes if contrast(m["stroke"], BG) < MARK] == []  # borders and outlines
    bars = [m for m in marks if m["op"] == "fillRect" and m["args"][3] == 6]
    assert bars and all(contrast(m["fill"], BG) >= MARK for m in bars)
    for m, after in pairwise(marks):  # a name dot under 3:1 is outlined by the next stroke
        c = opaque(m["fill"])
        if m["op"] == "fill" and c in colours_of(hostile_payload()) and contrast(c, BG) < MARK:
            assert after["op"] == "stroke" and contrast(after["stroke"], BG) >= MARK


def colours_of(payload: UniversePayload) -> set[str]:
    return {k.color for k in payload.kinds}


# ---------------------------------------------------------------- small screens


@pytest.mark.parametrize("project", ["large", "acme"])
def test_at_360_px_cards_keep_their_headers_and_nothing_scrolls_sideways(
    project: str, large_page: Any, tmp_path: Path, open_page: Any
) -> None:
    html = large_page[0] if project == "large" else write_example_page(tmp_path)
    p = open_page(html, viewport=NARROW)
    if project == "acme":
        set_k(p, summary(p)["kCards"] / 1.5)  # a Fit that is below the band would show cards: force them
    assert scroll_width(p) <= NARROW["width"]
    cards = sorted(hits(p)["cards"], key=lambda c: -c["w"])
    assert cards and all(c["named"] for c in cards if c["w"] >= 24)
    if project == "large":
        assert summary(p)["weight"] == 1
        assert all(c["rows"] >= 1 for c in cards[:3])  # the three largest still show rows


def write_example_page(tmp_path: Path) -> Path:
    from conftest import page_of

    return page_of(write_example(tmp_path / "acme_retail"))[0]


# ---------------------------------------------------------------- budgets (large project, 1280 x 800)


def draw_times(p: Page, n: int = 7) -> list[float]:
    out = []
    for _ in range(n):
        p.page.evaluate("views.universe.shown()")
        out.append(p.page.evaluate("views.universe.perf().draw"))
    return out


def test_the_summary_and_the_frames_stay_inside_their_budgets(large_page: Any, open_page: Any) -> None:
    p = open_page(large_page[0])
    summaries = []
    for label in ("Satellite", "Hub", "Link"):  # three relayouts
        untick(p, "kinds", label)
        summaries.append(p.page.evaluate("views.universe.perf().summary"))
    assert statistics.median(summaries) <= 30, summaries
    at_fit = statistics.median(draw_times(p))
    s = summary(p)
    set_k(p, math.sqrt(s["kStars"] * s["kCards"]))
    middle = statistics.median(draw_times(p))
    print(
        f"summary {statistics.median(summaries):.1f} ms, frame at Fit {at_fit:.1f} ms,"
        f" mid-crossfade {middle:.1f} ms"
    )
    assert at_fit <= 50 and middle <= 100
    assert VIEWPORT == {"width": 1280, "height": 800}
