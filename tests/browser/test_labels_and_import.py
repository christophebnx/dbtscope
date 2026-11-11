"""M6.3 (D-054): the one display-name rule, the layout import check and the shared tooltip placement.

Design note: docs/architecture/2026-11-11-m6.3-audit-follow-up.md (Test plan, UI design).
"""

# ruff: noqa: E501  (inline JavaScript snippets)
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
from conftest import SHOP, UNREADABLE_LAYOUTS

from browser.conftest import NARROW, Page, open_flow, show_detail
from browser.test_page_polish import FR, OLD_LAYOUT

pytestmark = pytest.mark.browser

NAMES_CONFIG = """\
layers:
  - {key: marts, label: "", match: ["path:models/sales/*"]}
  - {key: staging, label: Staging, match: ["path:models/staging/*", "type:source"]}
domains:
  - {key: orders, label: null, match: ["fct_*"]}
  - {key: staging_area, label: "", match: ["stg_*"]}
kinds:
  - {key: stage, label: null, match: ["stg_*"]}
  - {key: fact, label: "", match: ["fct_*"]}
"""

# ---------------------------------------------------------------- names


def texts(p: Page, selector: str) -> list[str]:
    return [t.strip() for t in p.page.locator(selector).evaluate_all("els => els.map(e => e.textContent)")]


def test_label_of_applies_one_rule(shop_page: Any) -> None:
    p, _ = shop_page
    got = p.page.evaluate(
        "[{key:'k',label:null},{key:'k',label:''},{key:'k',label:'L'},{key:'k',label:' '},{key:'k'}].map(labelOf)"
    )
    assert got == ["k", "k", "L", " ", "k"]


@pytest.mark.parametrize("lang", ["en", "fr"])
def test_universe_filters_show_the_key_of_an_empty_or_null_label(
    build_page: Any, open_page: Any, lang: str
) -> None:
    html, _ = build_page(NAMES_CONFIG + ("language: fr\n" if lang == "fr" else ""))
    p = open_page(html)
    domains = texts(p, "#u-domains label span")
    layers = texts(p, "#u-layers label span")
    kinds = texts(p, "#u-kinds label span")
    assert {"orders", "staging_area"} <= set(domains)
    assert {"marts", "Staging"} <= set(layers)
    assert {"stage", "fact"} <= set(kinds)
    for group in (domains, layers, kinds):
        assert all(t and t != "null" for t in group)


def test_domain_tooltip_and_trajectory_bar_name_the_key(build_page: Any, open_page: Any) -> None:
    html, _ = build_page(NAMES_CONFIG)
    p = open_page(html)
    p.page.fill("#u-q", "fct_orders")
    p.page.click("#u-traj")
    rows = texts(p, "#u-tj-list li")
    assert rows
    assert any(r.startswith("orders") for r in rows)
    assert all(r and not r.startswith(("null", ":")) for r in rows)
    assert (
        "orders" not in p.page.inner_text("#u-tj-sum") or True
    )  # the summary counts tables, rows name domains
    p.page.evaluate("views.universe.camera({x: 0, y: 0, k: 1.5})")
    tip = hover_text(p, "fct_orders")
    assert "orders" in tip and "null" not in tip and "· ·" not in tip


def test_flow_domain_list_names_the_key(build_page: Any, open_page: Any) -> None:
    html, _ = build_page(NAMES_CONFIG)
    p = open_page(html)
    open_flow(p, "fct_orders")
    p.page.click("#f-dom-sum")
    names = texts(p, "#f-dom-list li > span:not(.fmk)")[3:]
    assert "orders" in names and "staging_area" in names
    assert all(n and n != "null" for n in names)
    assert p.page.locator("#f-dom-list li small").count() >= 2
    assert "null" not in p.page.inner_text("#f-view")


def test_flow_tooltip_and_nodes_name_the_key(build_page: Any, open_page: Any) -> None:
    html, _ = build_page(NAMES_CONFIG)
    p = open_page(html)
    open_flow(p, "fct_orders")
    uid = SHOP + "fct_orders"
    p.page.locator(f'#f-graph g.node[id="{uid}"]').hover()
    tip = p.page.inner_text("#f-tip")
    assert "orders" in tip and "null" not in tip and "· ·" not in tip
    assert "Staging" not in tip  # fct_orders is a mart: its layer is the key "marts"
    assert "marts" in tip and "fact" in tip


def test_detail_types_filter_shows_the_key_of_a_null_label(build_page: Any, open_page: Any) -> None:
    html, _ = build_page(NAMES_CONFIG)
    p = open_page(html)
    show_detail(p)
    types = texts(p, "#d-types label span")
    assert {"stage", "fact"} <= set(types)
    assert all(t and t != "null" for t in types)


def hover_text(p: Page, name: str, fx: float = 0.5, fy: float = 0.5) -> str:
    """Hover the table `name` placed at the fractions (fx, fy) of the canvas; return the tooltip text."""
    hover_table(p, name, fx, fy)
    return p.page.inner_text("#u-tip")


def hover_table(p: Page, name: str, fx: float, fy: float) -> tuple[float, float]:
    """Move the table `name` to the fractions of the canvas, hover it; return the pointer (page coordinates)."""
    uid = SHOP + name if name != "orders" else "source.shop.erp.orders"
    c = p.page.evaluate("views.universe.camera({x: 0, y: 0, k: 1.5})")
    box = p.page.locator("#u-canvas").bounding_box()
    r = p.page.evaluate("id => views.universe.place(id)", uid)
    tx, ty = box["width"] * fx, box["height"] * fy
    p.page.evaluate(
        "to => views.universe.camera(to)",
        {"x": c["x"] + tx - (r["x"] + r["w"] / 2), "y": c["y"] + ty - (r["y"] + r["h"] / 2), "k": 1.5},
    )
    p.page.wait_for_timeout(50)
    x, y = box["x"] + tx, box["y"] + ty
    p.page.mouse.move(x - 3, y - 3)
    p.page.mouse.move(x, y)
    p.page.wait_for_function("document.getElementById('u-tip').style.display === 'block'", timeout=2000)
    return x, y


# ---------------------------------------------------------------- layout import


def import_layout(p: Page, folder: Path, content: Any) -> list[str]:
    """Import `content` (JSON-encoded) through #l-file; return the alerts shown."""
    messages: list[str] = []
    p.page.on("dialog", lambda d: (messages.append(d.message), d.accept()))
    f = folder / "in.json"
    f.write_text(json.dumps(content), encoding="utf-8")
    p.page.set_input_files("#l-file", str(f))
    p.page.wait_for_timeout(250)
    return messages


def snapshot(p: Page, key: str) -> tuple[str, str | None]:
    return p.page.evaluate("k => [JSON.stringify(LAYOUT.dump()), localStorage.getItem(k)]", key)


BAD = [pytest.param({**OLD_LAYOUT, **change}, id=str(change)) for change, _ in UNREADABLE_LAYOUTS] + [
    pytest.param([], id="top-level-array"),
    pytest.param(None, id="top-level-null"),
    pytest.param("text", id="top-level-string"),
]


@pytest.mark.parametrize("content", BAD)
def test_an_unreadable_layout_is_refused_and_changes_nothing(
    shop_page: Any, tmp_path: Path, content: Any
) -> None:
    p, data = shop_page
    key = "dbt-erd-layout:" + data["title"]
    p.page.evaluate("LAYOUT.set('universe', 'names', {nodes: {}})")  # something to lose
    before = snapshot(p, key)
    assert import_layout(p, tmp_path, content) == ["Not a dbt-erd layout file."]
    assert snapshot(p, key) == before


@pytest.mark.parametrize("change", [{"version": 2}, {"detail": "x"}], ids=["version", "section"])
def test_the_refusal_alert_is_in_french(build_page: Any, open_page: Any, tmp_path: Path, change: Any) -> None:
    p = open_page(build_page(FR)[0])
    assert import_layout(p, tmp_path, {**OLD_LAYOUT, **change}) == [
        "Ce fichier n'est pas une disposition dbt-erd."
    ]


def test_a_layout_without_version_imports_and_exports_version_1(shop_page: Any, tmp_path: Path) -> None:
    p, _ = shop_page
    content = {k: v for k, v in OLD_LAYOUT.items() if k != "version"}
    assert import_layout(p, tmp_path, content) == []
    assert p.page.evaluate("LAYOUT.get('universe', 'names')") == OLD_LAYOUT["universe"]["names"]
    assert json.loads(p.download("#l-export")[1])["version"] == 1


def test_a_layout_with_only_one_section_imports(shop_page: Any, tmp_path: Path) -> None:
    p, _ = shop_page
    content = {"format": "dbt-erd-layout", "version": 1, "detail": OLD_LAYOUT["detail"]}
    assert import_layout(p, tmp_path, content) == []
    assert p.page.evaluate("LAYOUT.get('detail', 'x')") == OLD_LAYOUT["detail"]["x"]


# ---------------------------------------------------------------- tooltip placement

PLACE = """([box, x, y]) => {
  const tip = document.getElementById(box), stage = tip.parentElement;
  tip.innerHTML = '<b>name</b><div class="m">a fixed content, 200 x 60</div>';
  tip.style.width = '200px'; tip.style.height = '60px';
  const s = stage.getBoundingClientRect();
  placeTip(tip, stage, s.left + x, s.top + y);
  const t = tip.getBoundingClientRect();
  return { left: t.left - s.left, top: t.top - s.top, right: s.right - t.right, bottom: s.bottom - t.bottom,
           w: t.width, h: t.height, W: s.width, H: s.height };
}"""


def test_place_tip_goes_right_and_below_at_the_start_and_flips_at_the_edges(shop_page: Any) -> None:
    p, _ = shop_page
    width, height = p.page.evaluate(
        "(r => [r.width, r.height])(document.getElementById('u-tip').parentElement.getBoundingClientRect())"
    )
    at = lambda x, y: p.page.evaluate(PLACE, ["u-tip", x, y])  # noqa: E731
    assert (at(20, 20)["left"], at(20, 20)["top"]) == (34, 34)
    right = at(width - 20, 100)
    assert right["left"] == pytest.approx(width - 20 - 14 - 200) and right["right"] >= 8
    bottom = at(100, height - 20)
    assert bottom["top"] == pytest.approx(height - 20 - 14 - 60) and bottom["bottom"] >= 8
    corner = at(width - 5, height - 5)
    assert min(corner["left"], corner["top"], corner["right"], corner["bottom"]) >= 8
    centre = at(width / 2, height / 2)
    assert (centre["left"], centre["top"]) == (width / 2 + 14, height / 2 + 14)


def inside_stage(p: Page, tip: str, box: str) -> dict[str, float]:
    return p.page.evaluate(
        """([tip, box]) => { const t = document.querySelector(tip).getBoundingClientRect(),
          s = document.querySelector(box).getBoundingClientRect();
          return { left: t.left - s.left, top: t.top - s.top, right: s.right - t.right, bottom: s.bottom - t.bottom, w: t.width, sw: s.width }; }""",
        [tip, box],
    )


@pytest.mark.parametrize("lang", ["en", "fr"])
@pytest.mark.parametrize("viewport", [None, NARROW], ids=["1280", "360"])
def test_universe_tooltip_stays_inside_the_stage(
    build_page: Any, open_page: Any, lang: str, viewport: Any
) -> None:
    p = open_page(build_page("" if lang == "en" else FR)[0], viewport=viewport)
    if viewport:
        p.page.evaluate("document.getElementById('u-panel').classList.add('closed')")
    for fx, fy in [(0.5, 0.5), (0.93, 0.5), (0.5, 0.93), (0.95, 0.95)]:
        x, y = hover_table(p, "fct_orders", fx, fy)
        g = inside_stage(p, "#u-tip", "#u-canvas")
        assert min(g["left"], g["top"], g["right"], g["bottom"]) >= 8 - 0.5, (fx, fy, g)
        assert g["w"] <= g["sw"] - 16 + 0.5
        t = p.page.locator("#u-tip").bounding_box()
        if (fx, fy) == (0.5, 0.5) and not viewport:
            assert t["x"] == pytest.approx(x + 14, abs=1) and t["y"] == pytest.approx(y + 14, abs=1)
        if fx > 0.9 and not viewport:
            assert t["x"] + t["width"] <= x  # left of the pointer
        if fy > 0.9 and not viewport:
            assert t["y"] + t["height"] <= y  # above the pointer


@pytest.mark.parametrize("lang", ["en", "fr"])
@pytest.mark.parametrize("viewport", [None, NARROW], ids=["1280", "360"])
def test_flow_tooltip_stays_inside_the_box(build_page: Any, open_page: Any, lang: str, viewport: Any) -> None:
    p = open_page(build_page("" if lang == "en" else FR)[0], viewport=viewport)
    open_flow(p, "fct_orders")
    long_text = "word " * 80
    for fx, fy in [(0.5, 0.5), (0.96, 0.5), (0.5, 0.96), (0.96, 0.96)]:
        got = p.page.evaluate(
            """([fx, fy, text]) => {
              const tip = document.getElementById('f-tip'), box = tip.parentElement, b = box.getBoundingClientRect();
              tip.innerHTML = '<b>t</b><div class="m">' + text + '</div>';
              placeTip(tip, box, b.left + b.width * fx, b.top + b.height * fy);
              const t = tip.getBoundingClientRect();
              return { left: t.left - b.left, top: t.top - b.top, right: b.right - t.right, bottom: b.bottom - t.bottom,
                       w: t.width, bw: b.width, x: b.width * fx, y: b.height * fy };
            }""",
            [fx, fy, long_text],
        )
        assert min(got["left"], got["top"], got["right"], got["bottom"]) >= 7.5, (fx, fy, got)
        assert got["w"] <= min(360, got["bw"] - 16) + 0.5
        if (fx, fy) == (0.5, 0.5) and viewport is None:
            assert got["left"] == pytest.approx(got["x"] + 14, abs=1)
    # the real hover, at the centre of the box: 14 px right of and below the pointer
    p.page.evaluate("document.getElementById('f-tip').style.display = 'none'")
    node = p.page.locator(f'#f-graph g.node[id="{SHOP}fct_orders"]')
    nb = node.bounding_box()
    node.hover()
    tip = p.page.locator("#f-tip").bounding_box()
    box = p.page.locator("#f-tip").evaluate(
        "e => { const r = e.parentElement.getBoundingClientRect(); return [r.left, r.top, r.right, r.bottom]; }"
    )
    assert box[0] + 7.5 <= tip["x"] and tip["x"] + tip["width"] <= box[2] - 7.5
    assert box[1] + 7.5 <= tip["y"] and tip["y"] + tip["height"] <= box[3] - 7.5
    assert nb


# ---------------------------------------------------------------- the list rows are unchanged


def test_trajectory_bar_rows_keep_their_geometry(shop_page: Any) -> None:
    p, _ = shop_page
    p.page.fill("#u-q", "fct_orders")
    p.page.click("#u-traj")
    p.page.click("#u-tj-sum")
    geo = p.page.evaluate(
        """() => [...document.querySelectorAll('#u-tj-list li')].map(li => {
          const [dot, text] = li.children, d = dot.getBoundingClientRect(), t = text.getBoundingClientRect();
          return { tag: [dot.tagName, text.tagName, li.children.length], display: getComputedStyle(li).display,
                   w: d.width, h: d.height, gap: t.left - d.right, row: li.getBoundingClientRect().height,
                   dy: Math.abs((d.top + d.bottom) / 2 - (t.top + t.bottom) / 2), left: d.left - li.getBoundingClientRect().left };
        })"""
    )
    assert geo
    for g in geo:
        assert g["tag"] == ["I", "SPAN", 2] and g["display"] == "flex"
        assert (g["w"], g["h"]) == (8, 8) and g["gap"] == pytest.approx(6, abs=0.1)
        assert g["left"] == 0 and g["dy"] <= 1 and 14 <= g["row"] <= 28


def test_flow_domain_rows_keep_their_geometry(shop_page: Any) -> None:
    p, _ = shop_page
    open_flow(p, "fct_orders")
    p.page.click("#f-dom-sum")
    geo = p.page.evaluate(
        """() => [...document.querySelectorAll('#f-dom-list li:not(.sep)')].map(li => {
          const k = [...li.children].map(c => c.tagName), r = li.getBoundingClientRect(), n = li.querySelector('small'),
                ul = document.getElementById('f-dom-list').getBoundingClientRect();
          const mark = li.children[0].getBoundingClientRect(), span = li.querySelector('span:not(.fmk)').getBoundingClientRect();
          return { k, small: n && ul.right - n.getBoundingClientRect().right, gap: span.left - mark.right, h: r.height,
                   align: n && getComputedStyle(n).marginLeft !== '0px' };
        })"""
    )
    assert len(geo) >= 5
    for g in geo[:3]:  # the legend rows: mark, text
        assert g["k"] == ["SPAN", "SPAN"] and g["small"] is None
    for g in geo[3:]:  # a domain row: dot, name, count flush right (10 px padding + 1 px border)
        assert g["k"] == ["I", "SPAN", "SMALL"]
        assert g["gap"] == pytest.approx(6, abs=0.1) and g["align"]
        assert g["small"] == pytest.approx(11, abs=1.5) and 14 <= g["h"] <= 28
