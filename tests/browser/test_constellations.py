"""Constellations by domain or by layer (M5.13, D-048): the switch `fieldset#u-by`, layer mode's geometry
on the example project, the config default, the per-viewer memory `dbtscope-constellations:<title>`, the
`layers:*` layout scopes, the tooltip, and what layer mode leaves unchanged (filters, search, trajectory,
flow, detail opening). Design note: docs/architecture/2026-11-05-m5.13-group-by-layers.md (test plan).
"""

from __future__ import annotations

import json
import math
import re
from itertools import pairwise
from pathlib import Path
from typing import Any

import pytest
from conftest import page_of, write_config, write_example

from browser.conftest import NARROW, Page, close_panel, open_flow, scroll_width, universe_page
from browser.test_trajectory_perf import median, universe_payload
from browser.test_universe_layout import (
    HOVER,
    LEVELS,
    OLD_ACME,
    assert_saved_layout_wins,
    frame,
    geometry,
    overlapping,
    rect,
    without_time,
)
from browser.test_zoom import drag, universe_at

pytestmark = pytest.mark.browser

TITLE = "ACME retail"  # the example's title
MEMORY = "dbtscope-constellations:" + TITLE
STORE = "dbt-erd-layout:" + TITLE
FR = "\u00a0: "  # L.colon in French (D-039)
# every storage call throws, as in a blocked or private context
NO_STORAGE = """for (const m of ['getItem', 'setItem', 'removeItem'])
  Storage.prototype[m] = () => { throw new DOMException('blocked', 'SecurityError'); };"""


def example(tmp_path: Path, extra: str = "", lang: str = "en") -> tuple[Path, dict[str, Any]]:
    """The example page, its config in `lang` and with `extra` appended; return it and its payload."""
    project = write_example(tmp_path / "acme_retail")
    config = (project / "dbt-erd.yml").read_text(encoding="utf-8")
    write_config(project, config.replace("language: en\n", f"language: {lang}\n") + extra)
    return page_of(project)


def choose(p: Page, by: str) -> None:
    p.page.check(f"#u-by input[value={by}]")


def checked(p: Page) -> str:
    return p.page.evaluate("document.querySelector('#u-by input:checked').value")


def memory(p: Page) -> str | None:
    return p.page.evaluate("k => localStorage.getItem(k)", MEMORY)


def stored_universe(p: Page) -> dict[str, Any]:
    return (p.page.evaluate("k => JSON.parse(localStorage.getItem(k))", STORE) or {}).get("universe", {})


def reload(p: Page) -> None:
    p.page.reload()
    p.page.wait_for_function("typeof views !== 'undefined' && !!views.universe", timeout=60_000)


def far_corner(c: dict[str, Any], t: dict[str, Any]) -> float:
    x0, y0, x1, y1 = rect(t)
    return math.hypot(max(abs(x0 - c["x"]), abs(x1 - c["x"])), max(abs(y0 - c["y"]), abs(y1 - c["y"])))


@pytest.fixture
def acme(tmp_path: Path, open_page: Any) -> tuple[Page, dict[str, Any]]:
    html, data = example(tmp_path)
    return open_page(html), data


# ---------------------------------------------------------------- visibility


def test_switch_is_hidden_and_ignored_below_two_layers(tmp_path: Path, open_page: Any) -> None:
    big = universe_payload().model_dump()
    keep = 40
    big["nodes"] = [{**n, "layer": "only"} for n in big["nodes"][:keep]]
    big["layers"] = [{"key": "only", "label": "Only"}]
    big["lineage"] = [e for e in big["lineage"] if max(e) < keep]
    big["relations"] = [e for e in big["relations"] if max(e) < keep]
    big["defaults"]["constellations"] = "layers"
    html = universe_page(tmp_path, type(universe_payload()).model_validate(big))
    p = open_page(html)
    p.page.evaluate("k => localStorage.setItem(k, 'layers')", "dbtscope-constellations:perf")
    reload(p)
    assert p.page.is_hidden("#u-by")
    g = geometry(p)
    assert g["by"] == "domains"
    assert {c["key"] for c in g["constellations"]} == {t["domain"] for t in g["tables"]}


def test_switch_shows_both_choices_and_their_counts(acme: tuple[Page, dict[str, Any]]) -> None:
    p, data = acme
    assert p.page.is_visible("#u-by") and checked(p) == "domains"
    assert p.page.inner_text("#u-h-by").lower() == "constellations"
    assert p.page.inner_text("#u-by-domains-n") == str(len(data["universe"]["domains"]))
    assert p.page.inner_text("#u-by-layers-n") == str(len(data["universe"]["layers"]))
    # first in the panel, above Links
    assert p.page.evaluate("document.getElementById('u-panel').firstElementChild.id") == "u-by"


# ---------------------------------------------------------------- layer mode on the example


def assert_layer_geometry(g: dict[str, Any], data: dict[str, Any], level: str) -> None:
    layers = [layer["key"] for layer in data["universe"]["layers"]]
    domains = [d["key"] for d in data["universe"]["domains"]]
    cs = g["constellations"]
    assert g["by"] == "layers"
    assert sorted(c["key"] for c in cs) == sorted({t["layer"] for t in g["tables"]}), level
    assert {t["layer"] for t in g["tables"]} == set(layers), level  # every layer of the example is shown
    xs = sorted(cs, key=lambda c: layers.index(c["key"]))
    assert all(a["x"] < b["x"] for a, b in pairwise(xs)), (level, [(c["key"], c["x"]) for c in xs])
    by_key = {c["key"]: c for c in cs}
    for t in g["tables"]:
        assert far_corner(by_key[t["layer"]], t) <= by_key[t["layer"]]["r"], (level, t["id"])
    for c in cs:
        keys = [b["key"] for b in c["bands"]]
        assert keys == [k for k in domains if k in keys], (level, c["key"], keys)
        members = [t for t in g["tables"] if t["layer"] == c["key"]]
        assert {t["domain"] for t in members} == set(keys), (level, c["key"])
        for left, right in pairwise(keys):
            edge = max(t["x"] + t["w"] / 2 for t in members if t["domain"] == left)
            start = min(t["x"] - t["w"] / 2 for t in members if t["domain"] == right)
            assert edge < start, (level, c["key"], left, right)
    found = overlapping([rect(t) for t in g["tables"]])
    assert not found, (level, found[:5])


def test_layer_mode_gives_one_constellation_per_layer_in_flow_order(
    acme: tuple[Page, dict[str, Any]],
) -> None:
    p, data = acme
    choose(p, "layers")
    for level in LEVELS:
        assert_layer_geometry(geometry(p, level), data, level)


def test_layer_mode_is_deterministic_across_loads(tmp_path: Path, open_page: Any) -> None:
    html, _ = example(tmp_path)
    first, second = open_page(html), open_page(html)
    for p in (first, second):
        choose(p, "layers")
    assert without_time(geometry(first)) == without_time(geometry(second))


def test_big_universe_in_layer_mode_reads_left_to_right_within_budget(tmp_path: Path, open_page: Any) -> None:
    """The 1,500-table payload: layer constellations strictly left to right in flow order at every
    detail level, laid out within the domain-mode budget (test_universe_layout.py), first time included."""
    p = open_page(universe_page(tmp_path, universe_payload()))
    choose(p, "layers")
    layers = p.page.evaluate("PAGE.universe.layers.map(l => l.key)")
    first = geometry(p)["layoutMs"]
    layouts: dict[str, list[float]] = {level: [] for level in LEVELS}
    for _ in range(3):
        for level in LEVELS:
            g = geometry(p, level)
            assert g["by"] == "layers", level
            xs = sorted(g["constellations"], key=lambda c: layers.index(c["key"]))
            assert [c["key"] for c in xs] == layers, level
            assert all(a["x"] < b["x"] for a, b in pairwise(xs)), (level, [(c["key"], c["x"]) for c in xs])
            layouts[level].append(g["layoutMs"])
    print("M5.13 big universe layer-mode layout (ms):", round(first), layouts)
    assert first < 1000, first
    assert all(median(v) < 1000 for v in layouts.values()), layouts


def test_switching_back_gives_the_same_domain_geometry(acme: tuple[Page, dict[str, Any]]) -> None:
    p, _ = acme
    before = without_time(geometry(p))
    choose(p, "layers")
    layered = without_time(geometry(p))
    choose(p, "domains")
    assert without_time(geometry(p)) == before
    choose(p, "layers")
    assert without_time(geometry(p)) == layered


def test_meta_line_counts_layers_in_layer_mode(acme: tuple[Page, dict[str, Any]]) -> None:
    p, _ = acme
    n = len(geometry(p)["constellations"])
    assert re.search(rf"\b{n} domains\b", p.page.inner_text("#u-meta"))
    choose(p, "layers")
    n = len(geometry(p)["constellations"])
    assert re.search(rf"\b{n} layers\b", p.page.inner_text("#u-meta"))


# ---------------------------------------------------------------- config default and memory


def test_config_default_opens_in_layer_mode(tmp_path: Path, open_page: Any) -> None:
    html, data = example(tmp_path, "universe:\n  constellations: layers\n")
    assert data["universe"]["defaults"]["constellations"] == "layers"
    p = open_page(html)
    assert checked(p) == "layers" and geometry(p)["by"] == "layers"
    assert memory(p) is None
    choose(p, "domains")  # differs from this page's default: remembered
    assert memory(p) == "domains"
    reload(p)
    assert checked(p) == "domains" and geometry(p)["by"] == "domains"


def test_memory_is_kept_only_when_it_differs_from_the_default(acme: tuple[Page, dict[str, Any]]) -> None:
    p, _ = acme
    assert memory(p) is None
    choose(p, "layers")
    assert memory(p) == "layers"
    reload(p)
    assert checked(p) == "layers" and geometry(p)["by"] == "layers"
    choose(p, "domains")
    assert memory(p) is None
    assert "constellations" not in json.dumps(stored_universe(p))  # never in the shared layout


def test_a_garbage_memory_is_ignored(acme: tuple[Page, dict[str, Any]]) -> None:
    p, _ = acme
    p.page.evaluate("k => localStorage.setItem(k, 'rows')", MEMORY)
    reload(p)
    assert checked(p) == "domains" and geometry(p)["by"] == "domains"


def test_switch_works_when_storage_throws(tmp_path: Path, open_page: Any) -> None:
    html, data = example(tmp_path)
    p = open_page(html)
    p.page.add_init_script(NO_STORAGE)
    reload(p)
    choose(p, "layers")
    assert_layer_geometry(geometry(p), data, "names")
    choose(p, "domains")
    assert geometry(p)["by"] == "domains"  # open_page checks that no error was reported


# ---------------------------------------------------------------- layout scopes


def drag_first_table(p: Page) -> str:
    """Drag the first drawn table by (40, 25) screen pixels at scale 1; return its id."""
    t = geometry(p)["tables"][0]
    drag(p, *universe_at(p, t["x"], t["y"], 1), 40, 25)
    return t["id"]


def test_a_drag_in_layer_mode_saves_the_layers_scope_only(acme: tuple[Page, dict[str, Any]]) -> None:
    p, _ = acme
    domains = without_time(geometry(p))
    choose(p, "layers")
    uid = drag_first_table(p)
    dragged = without_time(geometry(p))
    saved = stored_universe(p)
    assert set(saved) == {"layers:names"}
    scope = saved["layers:names"]
    assert set(scope["layers"]) == {c["key"] for c in dragged["constellations"]}
    assert uid in scope["nodes"]
    reload(p)
    assert without_time(geometry(p)) == dragged
    choose(p, "domains")
    assert without_time(geometry(p)) == domains  # a drag in one grouping never moves the other


def test_an_old_layout_file_loads_in_both_modes(acme: tuple[Page, dict[str, Any]], tmp_path: Path) -> None:
    p, data = acme
    choose(p, "layers")
    computed = without_time(geometry(p, "keys"))
    choose(p, "domains")
    uid = next(n["id"] for n in data["universe"]["nodes"] if n["name"] == "stg_erp__orders")
    layout = json.loads(json.dumps(OLD_ACME).replace("model.acme_retail.stg_erp__orders", uid))
    old = tmp_path / "dbt-erd-layout.json"
    old.write_text(json.dumps(layout), encoding="utf-8")
    p.page.set_input_files("#l-file", str(old))
    p.page.wait_for_function("!!LAYOUT.get('universe', 'keys')")
    assert_saved_layout_wins(geometry(p, "keys"), layout["universe"]["keys"])
    choose(p, "layers")
    assert without_time(geometry(p, "keys")) == computed


def test_export_import_and_reset_cover_both_groupings(
    acme: tuple[Page, dict[str, Any]], tmp_path: Path
) -> None:
    p, _ = acme
    drag_first_table(p)
    choose(p, "layers")
    drag_first_table(p)
    both = stored_universe(p)
    assert set(both) == {"names", "layers:names"}
    name, body = p.download("#l-export")
    assert json.loads(body)["universe"] == both
    p.page.on("dialog", lambda d: d.accept())
    p.page.click("#l-reset")
    assert stored_universe(p) == {}
    exported = tmp_path / name
    exported.write_bytes(body)
    p.page.set_input_files("#l-file", str(exported))
    p.page.wait_for_function("!!LAYOUT.get('universe', 'layers:names')")
    assert stored_universe(p) == both


# ---------------------------------------------------------------- tooltip


@pytest.mark.parametrize(
    ("lang", "domains", "domain", "action"),
    [
        ("en", "Domains: ", "Domain: ", "Double-click: zoom on this constellation"),
        ("fr", "Domaines" + FR, "Domaine" + FR, "Double-clic" + FR + "cadrer cette constellation"),
    ],
)
def test_layer_tooltip_lists_its_domains_and_names_the_band(
    tmp_path: Path, open_page: Any, lang: str, domains: str, domain: str, action: str
) -> None:
    html, data = example(tmp_path, lang=lang)
    p = open_page(html)
    choose(p, "layers")
    label = {d["key"]: d["label"] for d in data["universe"]["domains"]}
    g = geometry(p)
    c = max(g["constellations"], key=lambda c: len(c["bands"]))
    assert len(c["bands"]) >= 2
    frame(p, c["x"], c["y"], 1)
    x = (c["bands"][0]["x0"] + c["bands"][0]["x1"]) / 2  # inside the first band's own tables
    y = c["y"] + math.sqrt(c["r"] ** 2 - (x - c["x"]) ** 2) - 4  # near the rim, off any table
    text = p.page.evaluate(HOVER, [x, y])
    assert domains + " · ".join(label[b["key"]] for b in c["bands"]) in text, text
    first = c["bands"][0]["key"]
    n = sum(1 for t in g["tables"] if t["layer"] == c["key"] and t["domain"] == first)
    assert f"{domain}{label[first]} · {n} " in text, text
    assert text.endswith(action), text
    hint = p.page.inner_text("#u-hint")
    assert "constellation" in hint and ("domain by its name" not in hint)


# ---------------------------------------------------------------- unchanged behaviour in layer mode


def box(p: Page, panel: str, label: str) -> Any:
    return p.page.locator(f"#u-{panel} label", has_text=label).locator("input")


def test_unticking_a_layer_or_a_domain_removes_a_constellation_or_a_band(
    acme: tuple[Page, dict[str, Any]],
) -> None:
    p, data = acme
    choose(p, "layers")
    layer = data["universe"]["layers"][0]
    box(p, "layers", layer["label"]).uncheck()
    assert layer["key"] not in {c["key"] for c in geometry(p)["constellations"]}
    box(p, "layers", layer["label"]).check()
    dom = data["universe"]["domains"][0]
    box(p, "domains", dom["label"]).uncheck()
    g = geometry(p)
    assert g["constellations"] and all(
        dom["key"] not in {b["key"] for b in c["bands"]} for c in g["constellations"]
    )


def test_search_reveals_a_filtered_table_in_layer_mode(acme: tuple[Page, dict[str, Any]]) -> None:
    p, data = acme
    choose(p, "layers")
    n = next(n for n in data["universe"]["nodes"] if n["name"] == "fct_orders")
    layer = next(lay for lay in data["universe"]["layers"] if lay["key"] == n["layer"])
    box(p, "layers", layer["label"]).uncheck()
    assert n["id"] not in {t["id"] for t in geometry(p)["tables"]}
    p.page.fill("#u-q", "fct_orders")
    p.page.dispatch_event("#u-q", "change")
    p.page.wait_for_timeout(900)
    assert box(p, "layers", layer["label"]).is_checked()
    assert n["id"] in {t["id"] for t in geometry(p)["tables"]}
    assert p.page.evaluate("views.universe.camera().k") >= 1.5 - 1e-6


def test_switching_keeps_the_trajectory_and_frames_it(acme: tuple[Page, dict[str, Any]]) -> None:
    p, _ = acme
    p.page.fill("#u-q", "fct_orders")
    p.page.click("#u-traj")
    before = {k: v for k, v in p.state().items() if k != "layoutRuns"}
    assert before["active"] and before["up"]
    choose(p, "layers")
    assert {k: v for k, v in p.state().items() if k != "layoutRuns"} == before
    rect_ = p.page.evaluate("id => views.universe.place(id)", before["start"])
    w, h = p.page.evaluate("(c => [c.clientWidth, c.clientHeight])(document.getElementById('u-canvas'))")
    assert (
        rect_["x"] >= 0 and rect_["x"] + rect_["w"] <= w and rect_["y"] >= 0 and rect_["y"] + rect_["h"] <= h
    )


def test_flow_opens_and_closes_unchanged_in_layer_mode(acme: tuple[Page, dict[str, Any]]) -> None:
    p, _ = acme
    choose(p, "layers")
    g = without_time(geometry(p))
    s = open_flow(p, "fct_orders")
    assert s["open"]
    p.page.click("#f-back")
    assert not p.page.evaluate("flow.state().open")
    assert without_time(geometry(p)) == g and checked(p) == "layers"


def test_double_click_on_a_table_opens_the_detail_in_layer_mode(acme: tuple[Page, dict[str, Any]]) -> None:
    p, _ = acme
    choose(p, "layers")
    p.page.fill("#u-q", "fct_orders")
    p.page.dispatch_event("#u-q", "change")
    p.page.wait_for_timeout(900)
    b = p.page.locator("#u-canvas").bounding_box()
    p.page.mouse.dblclick(b["x"] + b["width"] / 2, b["y"] + b["height"] / 2)
    p.page.wait_for_selector("#tab-detail.on", timeout=10_000)


# ---------------------------------------------------------------- keyboard, names, narrow screens


def test_arrow_keys_switch_and_the_group_is_named(acme: tuple[Page, dict[str, Any]]) -> None:
    p, _ = acme
    group = p.page.get_by_role("group", name="Constellations")
    assert group.count() == 1
    assert group.get_by_role("radio").count() == 2
    p.page.get_by_role("radio", name="Domains").focus()
    p.page.keyboard.press("ArrowDown")
    assert checked(p) == "layers" and geometry(p)["by"] == "layers"
    assert p.page.evaluate("document.activeElement.value") == "layers"  # focus stays on the radio
    p.page.keyboard.press("ArrowUp")
    assert checked(p) == "domains" and geometry(p)["by"] == "domains"
    for select, name in (("#u-links", "links"), ("#u-detail", "tables")):
        assert (
            p.page.get_by_role("combobox", name=re.compile(name, re.I)).evaluate("e => '#' + e.id") == select
        )


def test_no_horizontal_scroll_at_360_px_in_french(tmp_path: Path, open_page: Any) -> None:
    html, _ = example(tmp_path, lang="fr")
    p = open_page(html, viewport=NARROW)
    close_panel(p, "u")
    assert scroll_width(p) <= NARROW["width"]
    p.page.click("#u-toggle")
    assert p.page.is_visible("#u-by")
    assert p.page.inner_text("#u-by-layers") == "Couches"
    choose(p, "layers")
    assert scroll_width(p) <= NARROW["width"]
    assert re.search(r"\b\d+ couches\b", p.page.inner_text("#u-meta"))
    p.page.click("#u-toggle")
    assert scroll_width(p) <= NARROW["width"]


def test_layer_mode_exports_the_png_under_the_same_name(acme: tuple[Page, dict[str, Any]]) -> None:
    p, _ = acme
    choose(p, "layers")
    name, body = p.download("#u-export")
    assert name == "ACME-retail-universe.png" and body.startswith(b"\x89PNG")
