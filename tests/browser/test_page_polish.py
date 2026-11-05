"""Page polish (M5.2, D-035): plural agreement, the shared escaper, the side panel on narrow screens,
and 44 px targets on touch screens. Design note: docs/architecture/2026-11-04-m5.2-page-polish.md.
M5.4 (D-038, D-039): French spacing, numbers in the page language, the detail panel cap, the shared
description line of the tooltips."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

import pytest
from conftest import SHOP, page_of, shop_manifest, write_config, write_example, write_manifest

from browser.conftest import (
    CENTRE_WAIT_MS,
    NARROW,
    Page,
    scroll_width,
    show_detail,
    universe_page,
    wait_exportable,
    wait_flow,
)
from browser.test_flow_perf import fan_payload
from browser.test_trajectory_perf import universe_payload as big_universe
from dbtscope.domain.payload import UniversePayload

pytestmark = pytest.mark.browser

FR = "language: fr\n"


def page_in(build_page: Any, open_page: Any, lang: str, **options: Any) -> Page:
    """The shop page in `lang`, opened with `options` (viewport, touch)."""
    return open_page(build_page("" if lang == "en" else FR)[0], **options)


def domain_box(p: Page, label: str) -> Any:
    return p.page.locator("#u-domains label", has_text=label).locator("input")


def meta(p: Page) -> str:
    return p.page.inner_text("#u-meta")


# ---------------------------------------------------------------- the plural helper


@pytest.mark.parametrize(
    ("lang", "tables", "columns"),
    [
        ("en", ["0 tables", "1 table", "2 tables"], ["0 columns", "1 column", "2 columns"]),
        ("fr", ["0 table", "1 table", "2 tables"], ["0 colonne", "1 colonne", "2 colonnes"]),
    ],
)
def test_plural_agrees_in_both_languages(
    build_page: Any, open_page: Any, lang: str, tables: list[str], columns: list[str]
) -> None:
    p = page_in(build_page, open_page, lang)
    assert p.page.evaluate("[0, 1, 2].map(n => plural(n, L.tables))") == tables
    assert p.page.evaluate("[0, 1, 2].map(n => plural(n, L.columns))") == columns


def test_string_tables_have_the_same_keys_and_pairs(shop_page: Any) -> None:
    p, _ = shop_page
    assert p.page.evaluate("Object.keys(STRINGS.en)") == p.page.evaluate("Object.keys(STRINGS.fr)")
    pairs = p.page.evaluate(
        "Object.values(STRINGS).flatMap(t => Object.entries(t)).filter(([, v]) => Array.isArray(v))"
        ".map(([k, v]) => [k, v.length])"
    )
    assert pairs and all(n == 2 for _, n in pairs), pairs


# ---------------------------------------------------------------- universe counts (acme_retail)

UNIVERSE_COUNTS = {
    "en": ("0 tables · 0 links · 0 domains", "1 table · 0 links · 1 domain", "tables", "2 domains"),
    "fr": ("0 table · 0 lien · 0 domaine", "1 table · 0 lien · 1 domaine", "tables", "2 domaines"),
}


def shared_tooltip(p: Page) -> str:
    """Hover the halo of the only shown domain, away from its table; return the tooltip's line."""
    box = p.page.locator("#u-canvas").bounding_box()
    x, y = box["x"] + box["width"] / 2, box["y"] + 46 + (box["height"] - 46) / 2
    for dy in range(60, 320, 20):
        p.page.mouse.move(x, y + dy)
        tip = p.page.locator("#u-tip")
        if tip.is_visible() and p.page.inner_text("#u-tip b") == "Shared":
            line = p.page.inner_text("#u-tip .m")
            if "·" not in line:
                return line
    raise AssertionError("no domain tooltip found on the halo of Shared")


@pytest.mark.parametrize("lang", ["en", "fr"])
def test_universe_meta_and_domain_tooltip_agree(tmp_path: Path, open_page: Any, lang: str) -> None:
    project = write_example(tmp_path / "acme_retail")
    config = (project / "dbt-erd.yml").read_text(encoding="utf-8")
    write_config(project, config.replace("language: en\n", f"language: {lang}\n"))
    p = open_page(page_of(project)[0])
    none, shared, tables, domains = UNIVERSE_COUNTS[lang]
    p.page.click("#u-none")
    assert meta(p) == none
    domain_box(p, "Shared").check()
    assert meta(p) == shared
    assert shared_tooltip(p) == "1 table"
    domain_box(p, "Finance").check()
    assert meta(p).split(" · ")[0].endswith(" " + tables) and meta(p).endswith(" " + domains), meta(p)


# ---------------------------------------------------------------- detail counts

DETAIL_COUNTS = {
    "en": ("1 / 1 table · 0 relations", "2 / 5 tables · 1 relation", "+ 1 column", "+ 2 columns"),
    "fr": ("1 / 1 table · 0 relation", "2 / 5 tables · 1 relation", "+ 1 colonne", "+ 2 colonnes"),
}


def node_text(p: Page, name: str) -> str:
    return p.page.evaluate("id => document.getElementById(id).textContent", SHOP + name)


@pytest.mark.parametrize("lang", ["en", "fr"])
def test_detail_meta_and_more_row_agree(
    dbt_project: Path, build_page: Any, open_page: Any, lang: str
) -> None:
    manifest = shop_manifest()  # dim_customer gets two non-key columns, dim_product keeps one
    manifest["nodes"][SHOP + "dim_customer"]["columns"]["email"] = {
        "name": "email",
        "data_type": "varchar",
        "description": "",
        "constraints": [],
    }
    write_manifest(dbt_project, manifest)
    p = open_page(build_page("" if lang == "en" else FR)[0])
    one_table, one_relation, one_column, two_columns = DETAIL_COUNTS[lang]
    show_detail(p)
    assert one_column in node_text(p, "dim_product")
    assert two_columns in node_text(p, "dim_customer")
    p.page.select_option("#d-group", "catalog")
    p.page.wait_for_function(f"document.getElementById('{SHOP}dim_product') !== null")
    assert p.page.inner_text("#d-meta").split(" · ")[:2] == one_table.split(" · ")
    p.page.select_option("#d-group", "sales")
    p.page.fill("#d-focus", "fct_returns")
    p.page.press("#d-focus", "Enter")
    assert p.page.inner_text("#d-meta").split(" · ")[:2] == one_relation.split(" · ")


# ---------------------------------------------------------------- trajectory


def test_one_table_brought_back_reads_singular_in_french(build_page: Any, open_page: Any) -> None:
    html, data = build_page(FR)
    p = open_page(html)
    orders = next(n for n in data["universe"]["nodes"] if n["name"] == "orders")
    label = next(d["label"] for d in data["universe"]["domains"] if d["key"] == orders["domain"])
    domain_box(p, label).uncheck()
    p.page.fill("#u-q", "fct_returns")
    p.page.click("#u-traj")
    assert p.page.inner_text("#u-tj-back") == "1 table ramenée par la trajectoire"
    assert "1 table ramenée par la trajectoire." in p.page.inner_text("#u-tj-live")


# ---------------------------------------------------------------- the shared escaper

NAME = "a<b&c\"d'e"
PAYLOAD = "<img src=x onerror=window.__x=1>"
LABEL = "<i>x</i>&\"'" + PAYLOAD
YAML_LABEL = "'" + LABEL.replace("'", "''") + "'"  # a YAML single-quoted scalar doubles its quote
ODD_CONFIG = (
    f"kinds:\n  - {{key: odd, label: {YAML_LABEL}, match: ['dim_*']}}\n"
    f"domains:\n  - {{key: odd, label: {YAML_LABEL}, color: '#4da3ff', match: ['schema:staging']}}\n"
)


def test_untrusted_names_and_labels_stay_text(dbt_project: Path, build_page: Any, open_page: Any) -> None:
    manifest = shop_manifest()
    returns = manifest["nodes"][SHOP + "fct_returns"]  # nothing refers to it by name
    returns["name"], returns["description"] = NAME, PAYLOAD
    write_manifest(dbt_project, manifest)
    html, data = build_page(ODD_CONFIG)
    assert NAME in {n["name"] for n in data["universe"]["nodes"]}
    assert LABEL in {d["label"] for d in data["universe"]["domains"]}
    p = open_page(html)
    assert p.page.evaluate("esc('<&\"\\'>')") == "&lt;&amp;&quot;&#39;&gt;"
    # universe: datalist, checkbox rows, tooltip
    assert NAME in p.page.evaluate("[...document.querySelectorAll('#u-names option')].map(o => o.value)")
    for panel in ("kinds", "domains"):
        assert LABEL in p.page.locator(f"#u-{panel} label span").all_text_contents()
        assert p.page.locator(f"#u-{panel} label span *").count() == 0
    p.page.fill("#u-q", NAME)
    p.page.dispatch_event("#u-q", "change")
    p.page.wait_for_timeout(CENTRE_WAIT_MS)
    box = p.page.locator("#u-canvas").bounding_box()
    p.page.mouse.move(box["x"] + box["width"] / 2, box["y"] + box["height"] / 2)
    assert p.page.text_content("#u-tip b") == NAME
    assert p.page.text_content("#u-tip").count(PAYLOAD) == 1  # the description, as text
    # detail: the node, the focus list, the types row
    show_detail(p)
    assert p.page.locator("#d-graph .msg").count() == 0
    assert NAME in node_text(p, "fct_returns")
    assert NAME in p.page.evaluate("[...document.querySelectorAll('#d-tables option')].map(o => o.value)")
    assert LABEL in p.page.locator("#d-types label span").all_text_contents()
    assert p.page.locator("#d-types label span *").count() == 0
    assert p.page.evaluate("typeof window.__x") == "undefined"


# ---------------------------------------------------------------- side panel on narrow screens (D-035)

PANELS = ("u", "d")


def panel_state(p: Page, view: str) -> tuple[bool, str]:
    return p.page.is_visible(f"#{view}-panel"), p.page.get_attribute(f"#{view}-toggle", "aria-expanded")


@pytest.mark.parametrize(("width", "is_open"), [(360, False), (600, False), (601, True), (1280, True)])
def test_panels_start_closed_at_600_px_or_narrower(
    build_page: Any, open_page: Any, width: int, is_open: bool
) -> None:
    p = open_page(build_page()[0], viewport={"width": width, "height": 800})
    expected = (is_open, str(is_open).lower())
    assert panel_state(p, "u") == expected
    show_detail(p, exportable=False)
    assert panel_state(p, "d") == expected
    if not is_open:  # one click opens each panel
        for view in ("d", "u"):
            if view == "u":
                p.page.click("#tabs button[data-tab=universe]")
            p.page.click(f"#{view}-toggle")
            assert panel_state(p, view) == (True, "true")


@pytest.mark.parametrize("touch", [False, True])
@pytest.mark.parametrize("lang", ["en", "fr"])
def test_open_panel_stacks_above_the_toolbar_at_360_px(
    build_page: Any, open_page: Any, lang: str, touch: bool
) -> None:
    p = page_in(build_page, open_page, lang, viewport=NARROW, touch=touch)
    for view in PANELS:
        if view == "d":
            show_detail(p, exportable=False)
        p.page.click(f"#{view}-toggle")
        panel = p.page.locator(f"#{view}-panel").bounding_box()
        toggle = p.page.locator(f"#{view}-toggle").bounding_box()
        assert scroll_width(p) <= NARROW["width"], view
        assert panel and toggle and panel["height"] <= 0.45 * NARROW["height"] + 1, panel
        assert p.page.is_visible(f"#{view}-toggle") and toggle["y"] >= panel["y"] + panel["height"] - 1


# ---------------------------------------------------------------- 44 px targets on touch screens

TARGETS = """() => {
  const sel = 'button, select, input:not([type=checkbox]):not([type=radio]):not([type=file]), '
    + '#u-tj-counts summary, .panel label, .panel h3 a';
  const out = [];
  document.querySelectorAll(sel).forEach(el => {
    const r = el.getBoundingClientRect();
    if (!el.getClientRects().length || !r.width) return;   // not displayed
    const name = el.id || el.textContent.trim().slice(0, 20) || el.tagName;
    if (r.height < 43.5) out.push(`${name}: height ${r.height}`);
    if (el.tagName === 'BUTTON' && r.width < 43.5) out.push(`${name}: width ${r.width}`);
  });
  return out;
}"""


def assert_targets(p: Page, where: str) -> None:
    assert p.page.evaluate(TARGETS) == [], where
    assert scroll_width(p) <= NARROW["width"], where


@pytest.mark.parametrize("lang", ["en", "fr"])
def test_every_control_is_a_44_px_target_on_touch_screens(build_page: Any, open_page: Any, lang: str) -> None:
    p = page_in(build_page, open_page, lang, viewport=NARROW, touch=True)
    assert p.page.evaluate("matchMedia('(pointer: coarse)').matches"), "touch emulation did not apply"
    assert_targets(p, "universe, panel closed")
    p.page.click("#u-toggle")
    assert p.page.locator("#u-panel label").count() > 0
    assert_targets(p, "universe, panel open")
    rows = p.page.locator("#u-by label")
    assert rows.count() == 2 and p.page.is_visible("#u-by")  # the radio rows are among the targets
    assert all(rows.nth(j).bounding_box()["height"] >= 43.5 for j in range(2))
    p.page.click("#u-toggle")
    p.page.fill("#u-q", "stg_orders")
    p.page.click("#u-traj")
    assert p.page.is_visible("#u-trajbar")
    assert_targets(p, "universe, trajectory bar open")
    show_detail(p, exportable=False)
    assert_targets(p, "detail, panel closed")
    p.page.click("#d-toggle")
    assert_targets(p, "detail, panel open")
    for field in ("#d-focus", "#d-q"):
        assert p.page.locator(field).bounding_box()["height"] == 44, field
    p.page.click("#tabs button[data-tab=universe]")
    assert p.page.locator("#u-q").bounding_box()["height"] == 44


def test_fine_pointer_keeps_the_desktop_sizes(shop_page: Any) -> None:
    p, _ = shop_page
    assert not p.page.evaluate("matchMedia('(pointer: coarse)').matches")
    assert p.page.evaluate("getComputedStyle(document.getElementById('l-reset')).minHeight") in (
        "auto",
        "0px",
    )
    assert p.page.locator("#l-reset").bounding_box()["height"] < 44


# ---------------------------------------------------------------- every count agrees (gap hunt)

COUNT = re.compile(r"^(\d+) (\S+)$")


def agrees(text: str, lang: str) -> list[int]:
    """Check that each "N noun" part of a meta line agrees in number; return the numbers."""
    numbers = []
    for part in text.split(" · "):
        found = COUNT.match(part.split(" / ")[-1])
        if not found:
            continue
        n, noun = int(found[1]), found[2]
        singular = n == 1 or (n == 0 and lang == "fr")
        assert noun.endswith("s") != singular, text
        numbers.append(n)
    return numbers


@pytest.mark.parametrize("lang", ["en", "fr"])
def test_every_universe_and_detail_meta_count_agrees(tmp_path: Path, open_page: Any, lang: str) -> None:
    project = write_example(tmp_path / "acme_retail")
    config = (project / "dbt-erd.yml").read_text(encoding="utf-8")
    write_config(project, config.replace("language: en\n", f"language: {lang}\n"))
    html, data = page_of(project)
    p = open_page(html)
    links: set[int] = set()
    labels = [d["label"] for d in data["universe"]["domains"]]
    for first, second in zip(labels, [*labels[1:], None], strict=True):
        p.page.click("#u-none")
        domain_box(p, first).check()
        links.add(agrees(meta(p), lang)[1])
        if second:
            domain_box(p, second).check()
            links.add(agrees(meta(p), lang)[1])
    assert 0 in links and max(links) >= 2, links  # 0 and 2+ links (1 link: the shop test below)
    show_detail(p, exportable=False)
    relations: set[int] = set()
    for group in p.page.eval_on_selector_all("#d-group option", "os => os.map(o => o.value)"):
        p.page.select_option("#d-group", group)
        relations.add(agrees(p.page.inner_text("#d-meta"), lang)[-1])
    assert max(relations) >= 2, relations


@pytest.mark.parametrize(
    ("lang", "expected"), [("en", "2 tables · 1 link · 1 domain"), ("fr", "2 tables · 1 lien · 1 domaine")]
)
def test_one_link_reads_singular(build_page: Any, open_page: Any, lang: str, expected: str) -> None:
    p = page_in(build_page, open_page, lang)
    p.page.click("#u-none")
    sales = p.page.locator("#u-domains label").filter(
        has=p.page.locator("span", has_text=re.compile("^sales$"))
    )
    sales.locator("input").check()
    assert meta(p) == expected


@pytest.mark.parametrize(
    ("lang", "one_hidden", "two_hidden", "two_back"),
    [
        (
            "en",
            "1 hidden by the filters",
            "2 hidden by the filters",
            "2 tables brought back by the trajectory",
        ),
        (
            "fr",
            "1 masquée par les filtres",
            "2 masquées par les filtres",
            "2 tables ramenées par la trajectoire",
        ),
    ],
)
def test_trajectory_counts_agree_in_both_languages(
    build_page: Any, open_page: Any, lang: str, one_hidden: str, two_hidden: str, two_back: str
) -> None:
    html, data = build_page("" if lang == "en" else FR)
    p = open_page(html)
    by_name = {n["name"]: n for n in data["universe"]["nodes"]}
    layers = {x["key"]: x["label"] for x in data["universe"]["layers"]}
    kinds = {k["key"]: k["label"] for k in data["universe"]["kinds"]}

    def layer_boxes() -> list[Any]:
        return [
            p.page.locator("#u-layers label", has_text=layers[by_name[n]["layer"]]).locator("input")
            for n in ("stg_orders", "dim_product")
        ]

    for box in layer_boxes():
        box.uncheck()
    p.page.fill("#u-q", "fct_returns")
    p.page.click("#u-traj")
    assert p.page.inner_text("#u-tj-back") == two_back
    assert two_back + "." in p.page.inner_text("#u-tj-live")
    p.page.locator("#u-kinds label", has_text=kinds[by_name["orders"]["kind"]]).locator("input").uncheck()
    assert p.page.inner_text("#u-tj-hidden") == one_hidden
    p.page.locator("#u-kinds label", has_text=kinds[by_name["orders"]["kind"]]).locator("input").check()
    for box in layer_boxes():
        box.uncheck()
    assert p.page.inner_text("#u-tj-hidden") == two_hidden


# ---------------------------------------------------------------- a hostile name in both views (gap hunt)

HOSTILE = "x</script><b>&\"'y"
TITLES = "els => els.map(e => (e.getAttribute('xlink:title') || '') + ' ' + e.textContent)"


def test_hostile_table_name_stays_text_in_both_views(
    dbt_project: Path, build_page: Any, open_page: Any
) -> None:
    manifest = shop_manifest()
    manifest["nodes"][SHOP + "dim_customer"]["name"] = HOSTILE  # a parent of relations
    write_manifest(dbt_project, manifest)
    html, _ = build_page()
    assert "x</script>" not in html.read_text(encoding="utf-8")  # the JSON writes < (D-023)
    p = open_page(html)
    assert HOSTILE in p.page.evaluate("[...document.querySelectorAll('#u-names option')].map(o => o.value)")
    p.page.fill("#u-q", HOSTILE)
    p.page.dispatch_event("#u-q", "change")
    p.page.wait_for_timeout(CENTRE_WAIT_MS)
    box = p.page.locator("#u-canvas").bounding_box()
    p.page.mouse.move(box["x"] + box["width"] / 2, box["y"] + box["height"] / 2)
    assert p.page.text_content("#u-tip b") == HOSTILE
    show_detail(p)
    assert p.page.locator("#d-graph .msg").count() == 0
    assert HOSTILE in node_text(p, "dim_customer")
    tips = " ".join(p.page.eval_on_selector_all("#d-graph svg a, #d-graph svg title", TITLES))
    assert f"· {HOSTILE}" in tips  # the node tooltip: "<group> · <name>"
    assert f"→ {HOSTILE}" in tips  # a relation tooltip towards it
    assert HOSTILE in p.page.evaluate("[...document.querySelectorAll('#d-tables option')].map(o => o.value)")


# ---------------------------------------------------------------- the layout file (invariant 9, D-013)

OLD_LAYOUT = {  # a file exported by a page before M5.2 (same shape as the reference page `edge`)
    "format": "dbt-erd-layout",
    "version": 1,
    "savedAt": "2026-11-01T09:00:00Z",
    "universe": {"names": {"domains": {"sales": [10, 20]}, "nodes": {SHOP + "dim_customer": [1, 2]}}},
    "detail": {"x": {SHOP + "dim_customer": [3, 4]}},
}


def test_layout_exported_before_m5_2_imports_and_exports_unchanged(shop_page: Any, tmp_path: Path) -> None:
    p, data = shop_page
    old = tmp_path / "dbt-erd-layout.json"
    old.write_text(json.dumps(OLD_LAYOUT), encoding="utf-8")
    p.page.set_input_files("#l-file", str(old))
    p.page.wait_for_function("!!LAYOUT.get('universe', 'names')")
    assert p.page.evaluate("LAYOUT.get('universe', 'names')") == OLD_LAYOUT["universe"]["names"]
    stored = p.page.evaluate(
        "key => JSON.parse(localStorage.getItem(key))", "dbt-erd-layout:" + data["title"]
    )
    assert stored["universe"] == OLD_LAYOUT["universe"] and stored["detail"] == OLD_LAYOUT["detail"]
    name, body = p.download("#l-export")
    exported = json.loads(body)
    assert name == "dbt-erd-layout.json"
    assert (exported["format"], exported["version"]) == ("dbt-erd-layout", 1)
    assert {k: exported[k] for k in ("universe", "detail")} == {
        k: OLD_LAYOUT[k] for k in ("universe", "detail")
    }


def test_a_file_of_another_format_is_refused(shop_page: Any, tmp_path: Path) -> None:
    p, _ = shop_page
    other = tmp_path / "other.json"
    other.write_text(json.dumps({**OLD_LAYOUT, "format": "something-else"}), encoding="utf-8")
    messages: list[str] = []
    p.page.on("dialog", lambda d: (messages.append(d.message), d.accept()))
    p.page.set_input_files("#l-file", str(other))
    p.page.wait_for_timeout(200)
    assert messages == ["Not a dbt-erd layout file."]
    assert p.page.evaluate("LAYOUT.get('universe', 'names')") is None


# ---------------------------------------------------------------- M5.4: French spacing (D-039)
# Design note: docs/architecture/2026-11-05-m5.4-contrast-touch-ups.md.

NBSP, NNBSP = "\u00a0", "\u202f"
# the page's own texts: text nodes (not in a script, style, datalist, or a Graphviz drawing, whose &#160; pad
# its labels), titles, aria-labels, placeholders
COLLECT = """() => {
  const out = [], walk = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
  for (let n; (n = walk.nextNode());) {
    const own = !n.parentElement.closest('script, style, datalist, svg');
    if (own && n.textContent.trim()) out.push(n.textContent);
  }
  document.querySelectorAll('[title], [aria-label], [placeholder]').forEach(e =>
    ['title', 'aria-label', 'placeholder'].forEach(a => {
      const v = e.getAttribute(a);
      if (v) out.push(v);
    }));
  return out;
}"""
# every value of STRINGS[lang]: strings, pairs, and what the functions return
STRING_VALUES = """lang => Object.values(STRINGS[lang]).flatMap(v =>
  typeof v === 'function' ? [v('7')] : Array.isArray(v) ? v : [v])"""
# Move the pointer over the canvas until the tooltip of a domain (with an owner when `owned`) shows;
# -> its name and count line
DOMAIN_TIP = """owned => {
  const c = document.getElementById('u-canvas'), tip = document.getElementById('u-tip');
  const r = c.getBoundingClientRect();
  const labels = new Set(PAGE.universe.domains.filter(d => !owned || d.owner).map(d => d.label));
  for (let y = r.top + 8; y < r.bottom; y += 8) for (let x = r.left + 8; x < r.right; x += 8) {
    c.dispatchEvent(new MouseEvent('mousemove', { clientX: x, clientY: y, bubbles: true }));
    const b = tip.querySelector('b'), m = tip.querySelector('.m');
    const shown = tip.style.display === 'block' && b && m;
    // a domain's count line is "N tables", plus " · owner: …" only when its dbt group has an owner
    const parts = shown && m.textContent.split(' · ').length;
    const domain = shown && labels.has(b.textContent) && parts === (owned ? 2 : 1);
    if (domain) return [b.textContent, m.textContent];
  }
  return null;
}"""
# hover the star of a table (universe), by its unique_id
HOVER_TABLE = """id => {
  const c = document.getElementById('u-canvas'), r = c.getBoundingClientRect(), p = views.universe.place(id);
  const at = { clientX: r.left + p.x + p.w / 2, clientY: r.top + p.y + p.h / 2, bubbles: true };
  c.dispatchEvent(new MouseEvent('mousemove', at));
  return document.getElementById('u-tip').innerHTML;
}"""
START = "dim_customer"  # an acme table with a description, upstream and downstream lineage


def data_strings(data: dict[str, Any]) -> list[str]:
    """Every string of the payload that is data (names, ids, descriptions, labels, owners), longest first."""
    u, d = data["universe"], data["detail"]
    out = {data["title"]}
    out |= {v for n in u["nodes"] for v in (n["id"], n["name"], n["desc"], *(c[0] for c in n["cols"]))}
    out |= {v for n in u["nodes"] for c in n["cols"] for v in c[:2]}
    out |= {v for k in ("domains", "layers", "kinds") for x in u[k] for v in (x["label"], x.get("owner", ""))}
    out |= {v for e in d["entities"] for v in (e["id"], e["name"], e["description"], e["group"])}
    out |= {v for e in d["entities"] for c in e["columns"] for v in c[:2]}
    return sorted((s for s in out if isinstance(s, str) and s.strip()), key=len, reverse=True)


def page_texts(p: Page, data: dict[str, Any]) -> list[str]:
    """The texts of the acme page after showing every composed string, the data taken out."""
    texts = list(p.page.evaluate(COLLECT))
    assert p.page.evaluate(DOMAIN_TIP, False), "no domain tooltip"
    texts += p.page.evaluate(COLLECT)
    start = next(n for n in data["universe"]["nodes"] if n["name"] == START)
    p.page.evaluate(HOVER_TABLE, start["id"])
    texts += p.page.evaluate(COLLECT)
    p.page.fill("#u-q", START)
    p.page.click("#u-traj")
    p.page.click("#u-tj-sum")
    texts += p.page.evaluate(COLLECT)
    p.page.click("#u-tj-flow")
    wait_flow(p)
    p.page.click("#f-dom-sum")
    p.page.locator("#f-graph g.node:not([aria-current])").first.hover()
    texts += p.page.evaluate(COLLECT)
    p.page.click("#f-back")
    texts += p.page.evaluate(COLLECT)
    show_detail(p)
    p.page.fill("#d-focus", START)
    p.page.press("#d-focus", "Enter")
    wait_exportable(p)
    p.download("#d-export-svg")
    p.page.wait_for_function("document.getElementById('export-live').textContent !== ''")
    texts += p.page.evaluate(COLLECT)
    texts += p.page.evaluate(STRING_VALUES, data["lang"])
    for value in data_strings(data):
        texts = [t.replace(value, "⁣") for t in texts]
    return texts


def misplaced(text: str) -> list[str]:
    """French: the marks of `text` not preceded by their no-break space."""
    return [
        text[max(0, i - 12) : i + 1]
        for i, ch in enumerate(text)
        if (ch == ":" and text[i - 1 : i] != NBSP) or (ch in "?!;" and text[i - 1 : i] != NNBSP)
    ]


def acme_in(tmp_path: Path, open_page: Any, lang: str) -> tuple[Page, dict[str, Any]]:
    project = write_example(tmp_path / "acme_retail")
    config = (project / "dbt-erd.yml").read_text(encoding="utf-8")
    write_config(project, config.replace("language: en\n", f"language: {lang}\n"))
    html, data = page_of(project)
    return open_page(html), {**data, "lang": lang}


def test_french_page_text_uses_french_spacing(tmp_path: Path, open_page: Any) -> None:
    p, data = acme_in(tmp_path, open_page, "fr")
    texts = page_texts(p, data)
    assert any(":" in t for t in texts) and any("?" in t for t in texts)
    assert [m for t in texts for m in misplaced(t)] == []
    assert p.page.evaluate("STRINGS.fr.colon") == NBSP + ": "


def test_english_page_text_has_no_space_before_marks(tmp_path: Path, open_page: Any) -> None:
    p, data = acme_in(tmp_path, open_page, "en")
    texts = page_texts(p, data)
    bad = [t for t in texts if NBSP in t or NNBSP in t or re.search(r" [:?!;]", t)]
    assert bad == []
    assert p.page.evaluate("Object.keys(STRINGS.en)") == p.page.evaluate("Object.keys(STRINGS.fr)")
    assert "colon" in p.page.evaluate("Object.keys(STRINGS.en)")


@pytest.mark.parametrize(("lang", "owner"), [("en", " · owner: Ana"), ("fr", f" · propriétaire{NBSP}: Ana")])
def test_domain_owner_shows_in_the_tooltip_and_the_list_with_the_page_spacing(
    build_page: Any, open_page: Any, lang: str, owner: str
) -> None:
    """acme has no dbt group (D-047): shop's sales_team group (owner Ana) carries the owner checks."""
    p = page_in(build_page, open_page, lang)
    name, line = p.page.evaluate(DOMAIN_TIP, True)
    assert name == "sales_team" and line.endswith(owner), line
    title = p.page.locator("#u-domains label", has_text=name).get_attribute("title")
    assert title == owner.removeprefix(" · "), title


# ---------------------------------------------------------------- M5.4: numbers (D-039)


@pytest.mark.parametrize(
    ("lang", "expected"),
    [
        ("en", ["1,234", "1,234 tables", "0 tables", "1 table"]),
        ("fr", [f"1{NNBSP}234", f"1{NNBSP}234 tables", "0 table", "1 table"]),
    ],
)
def test_numbers_follow_the_page_language(
    build_page: Any, open_page: Any, lang: str, expected: list[str]
) -> None:
    p = page_in(build_page, open_page, lang)
    assert (
        p.page.evaluate("[num(1234), plural(1234, L.tables), plural(0, L.tables), plural(1, L.tables)]")
        == expected
    )


def one_layer_payload() -> UniversePayload:
    """The 1,500-table universe of the trajectory performance test, every table in one layer."""
    data = big_universe().model_dump()
    data["nodes"] = [{**n, "layer": data["layers"][0]["key"]} for n in data["nodes"]]
    return UniversePayload.model_validate(data)


@pytest.mark.parametrize(("lang", "count"), [("en", "1,500"), ("fr", f"1{NNBSP}500")])
def test_large_counts_are_grouped(tmp_path: Path, open_page: Any, lang: str, count: str) -> None:
    p = open_page(universe_page(tmp_path, one_layer_payload(), language=lang))
    assert meta(p).startswith(f"{count} tables · "), meta(p)
    assert count in p.page.locator("#u-layers small").all_inner_texts()


@pytest.mark.parametrize(
    ("lang", "message"),
    [
        ("en", "Only 149 of the 1,499 tables at level 1 are drawn (at most 150 per flow)"),
        ("fr", f"Seules 149 des 1{NNBSP}499 tables du niveau 1 sont dessinées (au plus 150 par flux)"),
    ],
)
def test_flow_cap_message_groups_its_numbers(tmp_path: Path, open_page: Any, lang: str, message: str) -> None:
    p = open_page(universe_page(tmp_path, fan_payload(1499, 0), language=lang))
    p.page.fill("#u-q", "root")
    p.page.click("#u-traj")
    p.page.click("#u-tj-flow")
    wait_flow(p)
    assert p.page.inner_text("#f-cap") == message


# ---------------------------------------------------------------- M5.4: detail panel, narrow screens (D-038)

# the height of #d-graph with the detail panel open at 360 x 800, fine pointer (recorded for M5.4)
GRAPH_HEIGHT = {"en": 299, "fr": 268}


@pytest.mark.parametrize("touch", [False, True])
@pytest.mark.parametrize("lang", ["en", "fr"])
def test_open_detail_panel_takes_at_most_35_percent(
    build_page: Any, open_page: Any, lang: str, touch: bool
) -> None:
    p = page_in(build_page, open_page, lang, viewport=NARROW, touch=touch)
    p.page.click("#u-toggle")
    assert p.page.locator("#u-panel").bounding_box()["height"] <= 0.45 * NARROW["height"] + 1
    show_detail(p, exportable=False)
    p.page.click("#d-toggle")
    panel = p.page.evaluate(
        "() => { const e = document.getElementById('d-panel'); e.scrollTop = 40;"
        " return [e.getBoundingClientRect().height, e.scrollHeight > e.clientHeight, e.scrollTop]; }"
    )
    assert panel[0] <= 0.35 * NARROW["height"] + 1 and panel[1] and panel[2] > 0, panel
    graph = p.page.locator("#d-graph").bounding_box()["height"]
    assert graph > 0
    if not touch:
        assert abs(graph - GRAPH_HEIGHT[lang]) <= 10, graph
    assert scroll_width(p) <= NARROW["width"]


def test_detail_panel_is_beside_the_stage_at_601_px(build_page: Any, open_page: Any) -> None:
    p = open_page(build_page()[0], viewport={"width": 601, "height": 800})
    show_detail(p, exportable=False)
    panel = p.page.locator("#d-panel").bounding_box()
    stage = p.page.locator("#tab-detail .stage").bounding_box()
    assert panel["x"] + panel["width"] <= stage["x"] + 1 and panel["height"] > 0.35 * 800


# ---------------------------------------------------------------- M5.4: the M5.3 leftovers

DESC = """sel => {
  const d = document.querySelectorAll(sel + ' .desc'), e = d[0], s = e && getComputedStyle(e);
  return [d.length, e && e.textContent, s && s.color, s && s.marginTop, e && e.hasAttribute('style')];
}"""


def test_both_tooltips_share_one_description_line(tmp_path: Path, open_page: Any) -> None:
    p, data = acme_in(tmp_path, open_page, "en")
    start = next(n for n in data["universe"]["nodes"] if n["name"] == START)
    assert start["desc"]
    p.page.evaluate(HOVER_TABLE, start["id"])
    universe = p.page.evaluate(DESC, "#u-tip")
    p.page.fill("#u-q", START)
    p.page.click("#u-traj")
    p.page.click("#u-tj-flow")
    wait_flow(p)
    p.page.locator("#f-graph g.node[aria-current]").hover()
    flow_tip = p.page.evaluate(DESC, "#f-tip")
    fg = p.page.evaluate("getComputedStyle(document.body).color")
    assert universe == flow_tip == [1, start["desc"], fg, "6px", False]


def test_flow_shown_while_closed_does_nothing(shop_page: Any) -> None:
    p, _ = shop_page
    p.page.fill("#u-q", "stg_orders")
    p.page.click("#u-traj")
    p.page.click("#u-tj-flow")
    wait_flow(p)
    p.page.click("#f-back")
    # M5.10 (D-045): the d3 zoom needs no resize hook, so the flow handle has no `shown` any more
    assert p.page.evaluate("typeof flow.shown") == "undefined"
    p.page.set_viewport_size({"width": 900, "height": 700})
    assert p.page.evaluate("flow.isOpen()") is False
