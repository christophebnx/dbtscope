"""Page polish (M5.2, D-035): plural agreement, the shared escaper, the side panel on narrow screens,
and 44 px targets on touch screens. Design note: docs/architecture/2026-11-04-m5.2-page-polish.md."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

import pytest
from conftest import SHOP, page_of, shop_manifest, write_config, write_example, write_manifest

from browser.conftest import CENTRE_WAIT_MS, NARROW, Page, scroll_width, show_detail

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
  const sel = 'button, select, input:not([type=checkbox]):not([type=file]), #u-tj-counts summary, '
    + '.panel label, .panel h3 a';
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
