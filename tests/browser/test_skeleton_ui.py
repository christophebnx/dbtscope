"""The skeleton's panel, rows, announcements, counts, saved positions, export, narrow screen (M8.5).

`large_page` is the generated Data Vault project (group `vehicle`, 271 own tables + 12 dashed hubs, 135
satellites folded); `fan_detail` / `synthetic_detail` build small payloads for the cases the project has not.
"""

from __future__ import annotations

import re
import struct
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest
from conftest import page_of, write_layout
from large_project import write_large_project

from browser.conftest import (
    NARROW,
    Page,
    centre,
    detail_page,
    double_click,
    dstate,
    entities,
    fan_detail,
    scroll_width,
    show_detail,
    synthetic_detail,
    tooltip,
    untick,
    vehicle_hub,
    wait_drawn,
)

pytestmark = pytest.mark.browser

Large = tuple[Page, dict[str, Any]]
OpenPage = Callable[..., Page]
FOLD_KEY = "dbtscope-fold:Large vault"
FULL_KEY = "vehicle|||keys|hub,link,sat"  # the view key of a full drawing, as saved before M8.5


@pytest.fixture
def large_detail(large_page: Large) -> Large:
    p, data = large_page
    show_detail(p)
    return p, data


def drag(p: Page, table_id: str, dx: float = 25, dy: float = 15) -> None:
    box = p.page.locator(f"[id='{table_id}']").bounding_box()
    x, y = box["x"] + box["width"] / 2, box["y"] + box["height"] / 2
    p.page.mouse.move(x, y)
    p.page.mouse.down()
    p.page.mouse.move(x + dx, y + dy, steps=4)
    p.page.mouse.up()
    wait_drawn(p)


def edges(p: Page) -> int:
    return p.page.evaluate("document.querySelectorAll('#d-graph g.edge').length")


def among(data: dict[str, Any], ids: set[str]) -> int:
    return sum(r["child"] in ids and r["parent"] in ids for r in data["detail"]["relations"])


def held_by_parent(data: dict[str, Any]) -> dict[str, list[str]]:
    out: dict[str, list[str]] = {}
    for e in data["detail"]["entities"]:
        if e["parent"] and e["group"] == "vehicle":
            out.setdefault(e["parent"], []).append(e["id"])
    return out


# ---------------------------------------------------------------- no count is reduced


def test_the_folded_rows_sum_to_the_folded_tables_of_each_parent(large_detail: Large) -> None:
    p, data = large_detail
    s, held = dstate(p), held_by_parent(data)
    assert {k: sorted(v) for k, v in s["folded"].items()} == {k: sorted(v) for k, v in held.items()}
    counts = {}
    for parent, row in s["rows"].items():
        found = re.fullmatch(r"\+ (\d+) folded tables? · Satellite", row)
        assert found, row
        counts[parent] = int(found.group(1))
    assert counts == {k: len(v) for k, v in held.items()}
    assert sum(counts.values()) == 135


def test_folding_changes_what_is_drawn_never_what_is_counted(large_detail: Large) -> None:
    p, data = large_detail
    folded = dstate(p)
    types = p.page.inner_text("#d-types")
    ids = set(folded["drawn"]) | {i for v in folded["folded"].values() for i in v}
    assert len(ids) == 283 and folded["meta"].startswith("283 / 283 tables · ")
    assert edges(p) == among(data, set(folded["drawn"])) and f"· {edges(p)} relations" in folded["meta"]
    p.page.click("#d-fold-on")
    wait_drawn(p)
    shown = dstate(p)
    assert p.page.inner_text("#d-types") == types  # the Types list counts every table, folded or shown
    assert set(shown["drawn"]) == ids and shown["meta"].startswith("283 / 283 tables · ")
    assert shown["meta"] == f"283 / 283 tables · {among(data, ids)} relations · dashed: other group"
    assert edges(p) == among(data, ids)


# ---------------------------------------------------------------- kind filters while folded


def test_unticking_hubs_keeps_every_other_table_drawn_or_in_a_row(large_detail: Large) -> None:
    p, data = large_detail
    by_id = entities(data)
    before = dstate(p)
    scope = set(before["drawn"]) | {i for v in before["folded"].values() for i in v}
    untick(p, "Hub")
    s = dstate(p)
    visible = {i for i in scope if by_id[i]["kind"] != "hub"}
    rows = {i for i in visible if by_id[i]["parent"] in visible}
    assert s["skeleton"] is True
    assert set(s["drawn"]) == visible - rows  # a satellite whose hub is hidden stays a table
    assert {i for v in s["folded"].values() for i in v} == rows
    assert p.page.inner_text("#d-types").count("82") == 1  # the hubs (70 + 12 dashed) are still counted


# ---------------------------------------------------------------- the threshold


def test_more_than_sixty_tables_with_nothing_to_fold_draw_as_before(
    tmp_path: Path, open_page: OpenPage
) -> None:
    detail = fan_detail([], extra_hubs=61)
    p = open_page(detail_page(tmp_path, detail))
    show_detail(p)
    s = dstate(p)
    assert (len(s["drawn"]), s["skeleton"], s["rows"], s["warn"]) == (61, False, {}, "")
    assert p.page.is_hidden("#d-fold")  # nothing to fold: no control either


def test_sixty_one_tables_with_a_foldable_one_open_a_skeleton_and_show_the_control(
    tmp_path: Path, open_page: OpenPage
) -> None:
    p = open_page(detail_page(tmp_path, fan_detail([["sat"]], extra_hubs=59)))  # 60 hubs + 1 satellite
    show_detail(p)
    s = dstate(p)
    assert (s["skeleton"], len(s["drawn"]), len(s["folded"])) == (True, 60, 1)
    assert p.page.is_visible("#d-fold") and p.page.inner_text("#d-fold-n") == "1"


# ---------------------------------------------------------------- the fold control, shared by both views


def test_universe_fold_false_opens_both_views_unfolded(large_page_shown: Large) -> None:
    p, _ = large_page_shown
    p.page.click("#tabs button[data-tab=universe]")
    assert p.page.evaluate("views.universe.geometry().fold") == {"available": True, "on": False}
    show_detail(p)
    s = dstate(p)
    assert (s["fold"], s["skeleton"], len(s["drawn"])) == ({"available": True, "on": False}, False, 283)
    assert not p.page.is_checked("#d-fold-on") and s["warn"] == "283 tables: the drawing will be hard to read"
    assert (
        p.page.evaluate("localStorage.getItem('dbtscope-fold:Large vault')") is None
    )  # the default, not a choice


def test_a_change_made_in_the_universe_first_reaches_the_detail_and_one_key_holds_it(
    large_page: Large,
) -> None:
    p, _ = large_page
    p.page.click("#u-fold-on")  # fold off, in the universe, before the detail ever started
    show_detail(p)
    assert (dstate(p)["skeleton"], p.page.is_checked("#d-fold-on")) == (False, False)
    p.page.click("#d-fold-on")  # fold on again, in the detail
    wait_drawn(p)
    assert dstate(p)["skeleton"] is True
    p.page.click("#d-fold-on")
    wait_drawn(p)
    p.page.click("#tabs button[data-tab=universe]")
    assert p.page.evaluate("views.universe.geometry().fold.on") is False and not p.page.is_checked(
        "#u-fold-on"
    )
    keys = p.page.evaluate("Object.keys(localStorage).filter(k => k.includes('fold'))")
    assert keys == [FOLD_KEY] and p.page.evaluate("k => localStorage.getItem(k)", FOLD_KEY) == "shown"


def test_the_warning_is_a_polite_status_line_with_no_dialog(large_detail: Large) -> None:
    p, _ = large_detail
    dialogs: list[str] = []
    p.page.on("dialog", lambda d: (dialogs.append(d.type), d.dismiss()))
    assert (
        p.page.get_attribute("#d-fold-warn", "role") == "status" and p.page.inner_text("#d-fold-warn") == ""
    )
    assert p.page.inner_text("#d-fold-kinds") == "Satellite"
    p.page.click("#d-fold-on")
    wait_drawn(p)
    assert p.page.inner_text("#d-fold-warn") == "283 tables: the drawing will be hard to read"
    assert not dialogs and p.page.locator("dialog, [role=dialog], [role=alertdialog]").count() == 0
    p.page.click("#d-fold-on")
    wait_drawn(p)
    assert p.page.inner_text("#d-fold-warn") == ""


def test_the_hint_mentions_the_folded_rows_while_the_fold_is_on(large_detail: Large) -> None:
    p, _ = large_detail
    hint = 'a last row "+ N": double-click the table to draw them'
    assert hint in p.page.inner_text("#d-hint")
    p.page.click("#d-fold-on")
    wait_drawn(p)
    assert hint not in p.page.inner_text("#d-hint")


# ---------------------------------------------------------------- announcements


def test_the_page_announces_the_skeleton_and_the_return_to_a_full_drawing(large_detail: Large) -> None:
    p, data = large_detail
    live = "document.getElementById('d-live').textContent"
    assert p.page.get_attribute("#d-live", "role") == "status"
    assert p.page.evaluate(live) == "148 of 283 tables drawn, 135 folded tables as rows"
    p.page.evaluate("document.getElementById('d-live').textContent = 'kept'")
    drag(p, vehicle_hub(data))
    assert p.page.evaluate(live) == "kept"  # a drop redraws without announcing
    double_click(p, vehicle_hub(data))
    assert p.page.evaluate(live) == "All tables drawn"


def test_the_announcements_and_the_warning_in_french(tmp_path: Path, open_page: OpenPage) -> None:
    project = write_large_project(tmp_path / "large")
    config = project / "dbt-erd.yml"
    config.write_text(config.read_text(encoding="utf-8") + "language: fr\n", encoding="utf-8")
    html, data = page_of(project)
    p = open_page(html)
    show_detail(p)
    live = "document.getElementById('d-live').textContent"
    assert p.page.evaluate(live) == "148 tables dessinées sur 283, 135 tables repliées en lignes"
    hint = "une dernière ligne «\u00a0+ N\u00a0»\u00a0: double-cliquer la table"
    assert hint in p.page.inner_text("#d-hint")
    double_click(p, vehicle_hub(data))
    assert p.page.evaluate(live) == "Toutes les tables sont dessinées"
    p.page.evaluate("views.detail.focus(null)")
    p.page.click("#d-clear")
    wait_drawn(p)
    p.page.click("#d-fold-on")
    wait_drawn(p)
    assert p.page.inner_text("#d-fold-warn") == "283 tables\u00a0: le schéma sera difficile à lire"
    assert p.page.inner_text("#d-fold-t") == "Replier les tables descriptives dans leur entité"
    assert p.page.get_attribute("#d-fold label", "title").startswith("Dessiner chaque table descriptive")


# ---------------------------------------------------------------- the row and its tooltip


@pytest.mark.parametrize(("folded", "rest"), [(8, None), (9, "+ 1"), (12, "+ 4")])
def test_a_tooltip_lists_eight_folded_tables_then_the_rest(
    tmp_path: Path, open_page: OpenPage, folded: int, rest: str | None
) -> None:
    p = open_page(detail_page(tmp_path, fan_detail([["sat"] * folded], extra_hubs=55)))
    show_detail(p)
    hub = "model.s.h000_hub"
    names = [f"h000_sat{i:04d}" for i in range(folded)]
    lines = [f"{n} · Satellite" for n in names[:8]] + ([rest] if rest else [])
    assert tooltip(p, hub) == "\n".join(["g · h000_hub", "", f"{folded} folded tables:", *lines])
    assert dstate(p)["rows"][hub] == f"+ {folded} folded tables · Satellite"


@pytest.mark.parametrize(
    ("lang", "singular", "several", "counted"),
    [
        ("en", "+ 1 folded table · Satellite", "+ 4 folded tables · Satellite 3, PIT 1", "8 folded tables"),
        (
            "fr",
            "+ 1 table repliée · Satellite",
            "+ 4 tables repliées · Satellite 3, PIT 1",
            "8 tables repliées",
        ),
    ],
)
def test_rows_agree_with_their_number_and_list_at_most_two_kinds(
    tmp_path: Path, open_page: OpenPage, lang: str, singular: str, several: str, counted: str
) -> None:
    fans = [["sat", "sat", "sat", "pit"], ["sat"], ["sat", "pit", "ref"]]
    p = open_page(detail_page(tmp_path, fan_detail(fans, lang=lang, extra_hubs=60), language=lang))
    show_detail(p)
    rows = dstate(p)["rows"]
    assert rows["model.s.h000_hub"] == several and rows["model.s.h001_hub"] == singular
    assert rows["model.s.h002_hub"].endswith("· Satellite 1, PIT 1, + 1")
    meta = dstate(p)["meta"]
    assert f"{counted} (Satellite 5, PIT 2, + 1)" in meta  # the meta line lists two kinds, then the others


def test_a_row_writes_its_number_in_the_page_language(tmp_path: Path, open_page: OpenPage) -> None:
    for lang, text in (
        ("en", "+ 1,200 folded tables · Satellite"),
        ("fr", "+ 1\u202f200 tables repliées · Satellite"),
    ):
        folder = tmp_path / lang
        folder.mkdir()
        p = open_page(
            detail_page(folder, fan_detail([["sat"] * 1200], lang=lang, extra_hubs=60), language=lang)
        )
        show_detail(p)
        assert dstate(p)["rows"]["model.s.h000_hub"] == text


# ---------------------------------------------------------------- saved positions


def large_with_layout(
    tmp_path: Path, hub: str | None = None, fold: bool = True
) -> tuple[Path, dict[str, Any]]:
    """The large project, its layout holding a full-drawing arrangement (a hub's satellite and link pinned
    900 pt apart) saved before M8.5, and `universe.fold: false` unless `fold`."""
    project = write_large_project(tmp_path / "large")
    data = page_of(project)[1]
    by_id = entities(data)
    hub = hub or vehicle_hub(data)
    sat = next(i for i, e in sorted(by_id.items()) if e["parent"] == hub)
    link = next(
        i
        for i, e in sorted(by_id.items())
        if e["kind"] == "link"
        and hub in {r["parent"] for r in data["detail"]["relations"] if r["child"] == i}
    )
    write_layout(
        project,
        {"format": "dbt-erd-layout", "version": 1, "detail": {FULL_KEY: {sat: [0, 0], link: [900, 0]}}},
    )
    if not fold:
        config = project / "dbt-erd.yml"
        config.write_text(config.read_text(encoding="utf-8") + "universe:\n  fold: false\n", encoding="utf-8")
    html, data = page_of(project)
    return html, {"data": data, "sat": sat, "link": link, "hub": hub}


def test_a_layout_saved_before_m85_still_pins_the_full_drawing_when_the_fold_is_off(
    tmp_path: Path, open_page: OpenPage
) -> None:
    html, known = large_with_layout(tmp_path, fold=False)
    p = open_page(html)
    show_detail(p)
    assert dstate(p)["skeleton"] is False and len(dstate(p)["drawn"]) == 283
    (x0, y0), (x1, y1) = centre(p, known["sat"]), centre(p, known["link"])
    assert (round(x1 - x0), round(y1 - y0)) == (900, 0)


def test_that_layout_leaves_the_skeleton_as_laid_out_and_keeps_the_hidden_position(
    tmp_path: Path, open_page: OpenPage
) -> None:
    html, known = large_with_layout(tmp_path)
    p = open_page(html)
    show_detail(p)
    s = dstate(p)
    assert s["skeleton"] is True and known["sat"] not in s["drawn"]
    baseline = p.page.evaluate("views.detail.state().dot")
    assert "pos=" not in baseline  # no pinned render: the old key does not apply to a skeleton
    drag(p, known["hub"])
    stored = p.page.evaluate("LAYOUT.dump().detail")
    assert stored[FULL_KEY] == {known["sat"]: [0, 0], known["link"]: [900, 0]}  # untouched, not pruned
    assert list(stored) == [FULL_KEY, f"{FULL_KEY}|skeleton"]
    assert list(stored[f"{FULL_KEY}|skeleton"]) == [known["hub"]]
    p.page.click("#d-fold-on")  # the table is drawn again: its stored position applies again
    wait_drawn(p)
    (x0, y0), (x1, y1) = centre(p, known["sat"]), centre(p, known["link"])
    assert (round(x1 - x0), round(y1 - y0)) == (900, 0)


# ---------------------------------------------------------------- highlight, export, narrow screen


def test_a_click_on_an_entity_dims_all_but_it_and_its_drawn_neighbours(large_detail: Large) -> None:
    p, data = large_detail
    hub = vehicle_hub(data)
    near = {hub}
    for r in data["detail"]["relations"]:
        near |= {r["child"], r["parent"]} if hub in (r["child"], r["parent"]) else set()
    p.page.evaluate(
        "id => document.getElementById(id).dispatchEvent(new MouseEvent('click', { bubbles: true }))", hub
    )
    lit = p.page.evaluate("[...document.querySelectorAll('#d-graph g.node:not(.dim)')].map(g => g.id)")
    assert set(lit) == near & set(dstate(p)["drawn"]) and hub in lit and len(lit) > 1
    undimmed = p.page.evaluate("document.querySelectorAll('#d-graph g.edge:not(.dim)').length")
    assert undimmed == among(data, set(lit))
    p.page.evaluate(
        "document.querySelector('#d-graph svg').dispatchEvent(new MouseEvent('click', {bubbles: true}))"
    )
    assert p.page.evaluate("document.querySelectorAll('#d-graph .dim').length") == 0


def test_the_exports_of_a_skeleton_are_the_drawing(large_detail: Large) -> None:
    p, _ = large_detail
    rows = len(dstate(p)["rows"])
    name, svg = p.download("#d-export-svg")
    text = svg.decode("utf-8")
    assert name.endswith("-detail.svg") and text.count("folded table") == rows
    assert "skel-chain" not in text and "xlink:title" not in text  # no chain edge, no tooltip
    name, png = p.download("#d-export-png")
    width, height = struct.unpack(">II", png[16:24])
    assert name.endswith("-detail.png") and png[:8] == b"\x89PNG\r\n\x1a\n" and width > 800 and height > 600


def test_a_skeleton_at_360_px_has_no_horizontal_scroll_and_a_wrapping_meta_line(
    tmp_path: Path, open_page: OpenPage
) -> None:
    html, _ = page_of(write_large_project(tmp_path / "large"))
    p = open_page(html, viewport=NARROW)
    show_detail(p)
    assert dstate(p)["skeleton"] is True and scroll_width(p) <= NARROW["width"]
    lines = p.page.evaluate(
        """() => { const el = document.getElementById('d-meta'), r = document.createRange();
          r.selectNodeContents(el);
          return { lines: new Set([...r.getClientRects()].map(x => Math.round(x.top))).size,
                   fits: el.scrollWidth <= el.clientWidth + 1, right: el.getBoundingClientRect().right }; }"""
    )
    assert lines["lines"] >= 2 and lines["fits"] and lines["right"] <= NARROW["width"]


# ---------------------------------------------------------------- budgets


def test_all_groups_open_as_a_skeleton_within_the_budget(large_detail: Large) -> None:
    p, _ = large_detail
    p.page.select_option("#d-group", "")
    wait_drawn(p)
    times = [dstate(p)["layoutMs"]]
    for _ in range(2):
        p.page.evaluate("views.detail.relayout()")
        wait_drawn(p)
        times.append(dstate(p)["layoutMs"])
    s = dstate(p)
    assert (s["skeleton"], len(s["drawn"])) == (True, 788 - 421)  # 367 drawn, 421 folded into their entity
    assert s["meta"].startswith("788 / 788 tables · 421 folded tables (Satellite 421)")
    assert sorted(times)[1] < 5_000


def test_a_synthetic_group_of_1500_tables_draws_its_skeleton_with_rows(
    tmp_path: Path, open_page: OpenPage
) -> None:
    detail = synthetic_detail(hubs=300, links=300, sats=900)
    p = open_page(detail_page(tmp_path, detail))
    show_detail(p)
    s = dstate(p)
    assert len(s["drawn"]) == 600 and sum(len(v) for v in s["folded"].values()) == 900
    assert s["meta"].startswith("1,500 / 1,500 tables · 900 folded tables (Satellite 900)")
    assert 0.5 <= s["size"][0] / s["size"][1] <= 3


def test_unticking_the_last_folding_kind_keeps_the_skeleton_shape_with_no_row(large_detail: Large) -> None:
    p, _ = large_detail
    types = p.page.inner_text("#d-types")
    untick(p, "Satellite")
    s = dstate(p)
    assert s["skeleton"] is True and p.page.is_checked("#d-fold-on") and not p.page.is_hidden("#d-fold")
    assert s["folded"] == {} and s["rows"] == {}
    assert 0.5 <= s["size"][0] / s["size"][1] <= 3  # not the old strip
    assert p.page.inner_text("#d-types") == types  # counts unchanged
    assert s["meta"].startswith("148 / 283 tables · 0 folded tables · ")  # the scope still counts 283


def test_the_focus_box_announces_once_and_the_warning_replaces_the_live_text(large_detail: Large) -> None:
    p, data = large_detail
    live = "document.getElementById('d-live').textContent"
    hub = entities(data)["model.shop.vehicle_e001_hub"]["name"]
    assert "tables drawn" in p.page.evaluate(live)
    p.page.fill("#d-focus", hub)
    p.page.press("#d-focus", "Enter")  # Enter focuses; the change event on blur must not render again
    p.page.dispatch_event("#d-focus", "change")
    wait_drawn(p)
    p.page.wait_for_timeout(300)
    assert p.page.evaluate(live) == "All tables drawn"
    p.page.click("#d-clear")
    wait_drawn(p)
    assert "tables drawn" in p.page.evaluate(live)
    p.page.click("#d-fold-on")  # fold off: the full drawing is hard to read
    wait_drawn(p)
    assert dstate(p)["warn"] != "" and p.page.evaluate(live) == ""
