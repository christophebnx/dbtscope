from __future__ import annotations

import re
from typing import Any

import pytest
from conftest import DATA_OPEN, data_block, empty_detail, empty_universe, page_data

from dbtscope.domain.config import merge_config
from dbtscope.domain.layout import LAYOUT_FORMAT
from dbtscope.domain.payload import DetailPayload
from dbtscope.render import page as page_module
from dbtscope.render.page import ASSETS, LIBRARIES, VENDOR, render_page

DETAIL = empty_detail()
UNIVERSE = empty_universe()


def _detail(entity: dict[str, Any]) -> DetailPayload:
    """`DETAIL` with one entity."""
    return DetailPayload.model_validate({**DETAIL.model_dump(), "entities": [entity]})


def test_page_embeds_scripts_title_and_data() -> None:
    config = merge_config({}, {"title": "A & <B>", "view": "detail"})
    page = render_page(DETAIL, UNIVERSE, config, {"format": "dbt-erd-layout"})
    assert "<title>A &amp; &lt;B></title>" in page
    assert "function startUniverse" in page and "function startDetail" in page
    assert "{{" not in page
    data = page_data(page)
    assert data["view"] == "detail" and data["layout"] == {"format": "dbt-erd-layout"}


@pytest.mark.parametrize("offline", [False, True])
def test_comment_and_script_open_in_the_data_are_escaped(offline: bool) -> None:
    # "<!-- <script>" would put the HTML parser in script double-escaped state (D-023)
    text = "a <!-- <script> b </script> c"
    entity = {"id": "a", "name": "a", "group": "", "kind": "other", "description": text, "columns": []}
    config = merge_config({}, {"title": "<!-- <script>"})
    page = render_page(_detail(entity), UNIVERSE, config, offline=offline)
    assert b"<" not in data_block(page.encode("utf-8"))
    data = page_data(page)
    assert data["detail"]["entities"][0]["description"] == text and data["title"] == "<!-- <script>"


def test_page_has_the_trajectory_mode() -> None:
    page = render_page(DETAIL, UNIVERSE, merge_config({}, {}))
    for marker in (
        'id="u-trajbar"',
        'id="u-traj"',
        'id="u-tj-leave"',
        'id="u-tj-live"',
        "function trajectory(",
    ):
        assert marker in page


M1_SCRIPT_TAGS = """\
<script src="https://cdnjs.cloudflare.com/ajax/libs/d3/7.9.0/d3.min.js"></script>
<script src="https://cdnjs.cloudflare.com/ajax/libs/viz.js/2.1.2/viz.js"></script>
<script src="https://cdnjs.cloudflare.com/ajax/libs/viz.js/2.1.2/full.render.js"></script>"""


def test_cdn_page_keeps_the_m1_script_tags_but_svg_pan_zoom() -> None:
    page = render_page(DETAIL, UNIVERSE, merge_config({}, {}))
    after_data = page.split('id="data">', 1)[1].split("</script>\n", 1)[1]
    assert after_data.startswith(M1_SCRIPT_TAGS + "\n<script>\n// Page-wide")
    # M5.10 (D-045): d3 and Viz.js only, svg-pan-zoom left the page
    assert page.count("<script src") == 3
    assert "svg-pan-zoom" not in page and "svgPanZoom" not in page
    assert "/*! d3" not in page


def test_title_with_a_placeholder_is_not_substituted() -> None:
    page = render_page(DETAIL, UNIVERSE, merge_config({}, {"title": "{{DATA}}"}))
    assert "<title>{{DATA}}</title>" in page
    assert page_data(page)["title"] == "{{DATA}}"


def _offline_page() -> str:
    return render_page(DETAIL, UNIVERSE, merge_config({}, {}), offline=True)


CDN_HOSTS = ("cdnjs.cloudflare.com", "cdn.jsdelivr.net")


def test_offline_page_embeds_every_library_in_order_and_loads_no_remote_script() -> None:
    page = _offline_page()
    # M2: every opening <script> tag is a bare inline block (or the JSON payload): nothing to fetch
    assert set(re.findall(r"<script\b[^>]*>", page, re.IGNORECASE)) == {
        "<script>",
        DATA_OPEN,
    }
    assert not any(host in page for host in CDN_HOSTS)
    assert not re.search(r"""\bimport\s*\(\s*["']https?://""", page)
    assert len(re.findall(r"<script\b", page, re.IGNORECASE)) == len(re.findall(r"</script>", page, re.I))
    positions = [page.index(f"/*! {lib.name} {lib.version}, {lib.spdx}. Licence:") for lib in LIBRARIES[:2]]
    positions.append(page.index("Includes Graphviz 2.40.1, EPL-1.0. Licence:"))
    positions.append(page.index("// Page-wide"))
    assert positions == sorted(positions)
    assert "svg-pan-zoom" not in page and "svgPanZoom" not in page  # M5.10 (D-045)
    for lib in LIBRARIES:
        first = (VENDOR / lib.licence).read_text(encoding="utf-8").strip().splitlines()[0]
        assert first in page
    assert "Includes Expat 2.2.5, MIT. Licence:" in page
    assert page_data(page)["title"] == "dbt ERD"
    # minified libraries hold "{{" of their own: check no placeholder of the shell is left
    for name in ("STYLE", "SCRIPTS", "COMMON_JS", "DETAIL_JS", "UNIVERSE_JS", "BOOT_JS", "TITLE", "DATA"):
        assert "{{" + name + "}}" not in page


def test_inlined_libraries_cannot_close_their_script(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(page_module, "_vendored", lambda name: 'var a = "</script>", b = "</SCRIPT"; /* */')
    page = _offline_page()
    assert '"<\\/script>"' in page and '"<\\/SCRIPT"' in page
    assert "* /" in page  # a licence cannot end the banner comment early
    assert len(re.findall(r"<script\b", page, re.IGNORECASE)) == len(re.findall(r"</script>", page, re.I))


def test_page_has_the_export_controls() -> None:
    page = render_page(DETAIL, UNIVERSE, merge_config({}, {}))
    for marker in (
        'id="u-export"',
        'id="d-export-png"',
        'id="d-export-svg"',
        'id="export-live" role="status" aria-live="polite"',
        "const EXPORT =",
        "function svgImage(",
        "function image(",
    ):
        assert marker in page
    # the controls live in the toolbars, never in the drawn area
    for box in page.split('class="canvas-box"')[1:]:
        assert "export" not in box.split("</section>", 1)[0]


# ---------------------------------------------------------------- M2 acceptance gaps (tester)


def test_offline_page_carries_the_licence_texts_of_the_compiled_in_components() -> None:
    page = _offline_page()
    notices = [n for lib in LIBRARIES for n in lib.notices]
    assert {n.name for n in notices} == {"Graphviz", "Expat", "Emscripten", "musl"}
    assert "Includes musl 1.1.15, MIT. Licence:" in page
    for notice in notices:
        text = (VENDOR / notice.file).read_text(encoding="utf-8").strip()
        assert text.splitlines()[0] in page
        assert text.splitlines()[-1].replace("*/", "* /") in page  # the whole text, not a heading
    # banners are /*! comments, so minifiers and readers keep them
    assert page.count("/*! ") >= len(LIBRARIES)


def test_offline_banner_says_where_the_graphviz_source_is() -> None:
    page = _offline_page()
    start = page.index("Includes Graphviz 2.40.1, EPL-1.0. Licence:")
    section = page[start : page.index("Includes Expat", start)]
    assert "\nSource: https://gitlab.com/graphviz/graphviz/-/tree/2.40.1" in section
    assert page.count("\nSource: ") == 1  # only the notices that set one
    assert "Includes Emscripten 1.37.36, MIT OR NCSA. Licence:" in page


def test_offline_page_differs_from_the_cdn_page_only_in_the_scripts() -> None:
    cdn = render_page(DETAIL, UNIVERSE, merge_config({}, {}))
    offline = _offline_page()
    head, tail = cdn.split(M1_SCRIPT_TAGS)
    assert offline.startswith(head) and offline.endswith(tail)


# ---------------------------------------------------------------- M5.2: common.js, layout format


@pytest.mark.parametrize("offline", [False, True])
def test_common_script_comes_first_in_its_own_block(offline: bool) -> None:
    page = render_page(DETAIL, UNIVERSE, merge_config({}, {}), offline=offline)
    starts = [
        page.index("<script>\n" + first)
        for first in ("// Page-wide", "// Detail view", "// Universe view", "// Page boot")
    ]
    assert starts == sorted(starts)
    common = page[starts[0] : page.index("</script>", starts[0])]
    assert "const PAGE = JSON.parse" in common and "function startDetail" not in common
    assert len(re.findall(r"<script\b", page, re.IGNORECASE)) == len(re.findall(r"</script>", page, re.I))


def test_common_script_cannot_close_its_block() -> None:
    assert "</script" not in (ASSETS / "common.js").read_text(encoding="utf-8").lower()


def test_boot_writes_the_layout_format_once() -> None:
    boot = (ASSETS / "boot.js").read_text(encoding="utf-8")
    assert f"const LAYOUT_FORMAT = '{LAYOUT_FORMAT}';" in boot
    assert boot.count(f"'{LAYOUT_FORMAT}'") == 1
    assert f"'{LAYOUT_FORMAT}:' + PAGE.title" in boot  # the localStorage key is unchanged (invariant 9)


# ---------------------------------------------------------------- M5.3: the flow view (D-036)


def test_page_has_the_flow_view() -> None:
    page = render_page(DETAIL, UNIVERSE, merge_config({}, {}))
    for marker in (
        'id="f-view"',
        'id="u-tj-flow"',
        'id="f-export-png"',
        'id="f-export-svg"',
        'id="f-live"',
        "function startFlow(",
        "function flowRanks(",
    ):
        assert marker in page
    assert "{{FLOW_JS}}" not in page


def test_page_has_the_text_summary_of_the_constellations_inside_the_stage_after_the_canvas() -> None:
    page = render_page(DETAIL, UNIVERSE, merge_config({}, {}))
    stage = page[page.index('id="u-stage"') : page.index('id="tab-detail"')]
    assert stage.index('id="u-canvas"') < stage.index('id="u-summary"')
    summary = re.search(r"<section[^>]*\bid=\"u-summary\"[^>]*>(.*?)</section>", stage, re.S)
    assert summary is not None
    assert 'class="sr-only"' in summary.group(0) and 'aria-labelledby="u-summary-h"' in summary.group(0)
    assert re.search(r'<h2 id="u-summary-h">', summary.group(1))


def test_the_universe_panel_has_the_source_systems_list_and_the_dependencies_row() -> None:
    """M8.4, M9.1: a second Domains heading with its own all / none; the Dependencies row, with its
    "all (N)" toggle, after Links inside the Display group."""
    page = render_page(DETAIL, UNIVERSE, merge_config({}, {}))
    panel = page[page.index('id="u-panel"') : page.index('class="stage"')]
    assert panel.index('id="u-domains"') < panel.index('id="u-systems-h"') < panel.index('id="u-systems"')
    heading = re.search(r'<h3 id="u-systems-h">(.*?)</h3>', panel, re.S)
    assert heading is not None
    assert 'id="u-sys-all"' in heading.group(1) and 'id="u-sys-none"' in heading.group(1)
    row = re.search(r'<div id="u-routes-on-row" hidden>(.*?)</div>', panel, re.S)
    assert row is not None
    assert 'id="u-routes-on-box"' in row.group(1) and 'id="u-routes-box"' in row.group(1)
    assert panel.index('id="u-links"') < panel.index('id="u-routes-on-row"') < panel.index('id="u-cards-row"')
    assert 'id="u-routes-row"' not in panel


def test_the_universe_panel_is_navigate_display_filters() -> None:
    """M9.1 (D-085): three titled sections in this order, the hint out of the panel, Display's extra
    options in a <details> closed at load."""
    page = render_page(DETAIL, UNIVERSE, merge_config({}, {}))
    panel = page[page.index('id="u-panel"') : page.index('class="stage"')]
    sections = [panel.index(f'<section id="{i}"') for i in ("u-nav", "u-display", "u-filters")]
    assert sections == sorted(sections)
    for section, heading in (
        ("u-nav", "u-h-nav"),
        ("u-display", "u-h-display"),
        ("u-filters", "u-h-filters"),
    ):
        assert f'<section id="{section}" aria-labelledby="{heading}"><h2 id="{heading}"></h2>' in re.sub(
            r">\s+<", "><", panel
        )
    more = re.search(r"<details id=\"u-more\"([^>]*)>", panel)
    assert more is not None and "open" not in more.group(1)
    display = panel[panel.index('id="u-display"') : panel.index('id="u-filters"')]
    assert display.index('id="u-detail"') < display.index('id="u-more"')
    for inside in ("u-fold", "u-links", "u-routes-on-row", "u-cards-row"):
        assert display.index('id="u-more"') < display.index(f'id="{inside}"'), inside
    assert 'id="u-hint"' not in panel
    nav = panel[panel.index('id="u-nav"') : panel.index('id="u-display"')]
    assert nav.index('id="u-by"') < nav.index('id="u-domains"') < nav.index('id="u-systems"')
    filters = panel[panel.index('id="u-filters"') :]
    assert filters.index('id="u-layers"') < filters.index('id="u-kinds"')


def test_the_layout_menu_the_help_popovers_and_the_crumbs_are_in_the_markup() -> None:
    """M9.1 (D-085, D-086): the Layout menu holds the three layout buttons, each toolbar a Help popover
    that holds its hint, the detail toolbar a hidden trail after the panel button, a columns select."""
    page = render_page(DETAIL, UNIVERSE, merge_config({}, {}))
    menu = re.search(r'<details id="l-menu" class="menu">(.*?)</details>', page, re.S)
    assert menu is not None
    assert all(f'id="l-{i}"' in menu.group(1) for i in ("reset", "export", "import"))
    helps = re.findall(
        r'<details class="help"><summary id="(\w)-help-t"></summary><div class="help-pop" id="\w-hint">', page
    )
    assert helps == ["u", "d"]
    assert re.search(
        r'<button id="d-toggle"[^>]*>☰</button>\s*<nav id="d-crumbs" class="crumbs" hidden></nav>', page
    )
    assert re.search(r'<select id="d-cols"[^>]*></select>', page)
    assert "layout-actions" not in page


@pytest.mark.parametrize("offline", [False, True])
def test_scripts_come_in_order_common_detail_universe_flow_boot(offline: bool) -> None:
    page = render_page(DETAIL, UNIVERSE, merge_config({}, {}), offline=offline)
    starts = [
        page.index("<script>\n" + first)
        for first in ("// Page-wide", "// Detail view", "// Universe view", "// Flow view", "// Page boot")
    ]
    assert starts == sorted(starts)
    flow = page[starts[3] : page.index("</script>", starts[3])]
    assert "function startFlow(" in flow and "function startUniverse(" not in flow
    assert len(re.findall(r"<script\b", page, re.IGNORECASE)) == len(re.findall(r"</script>", page, re.I))


def test_no_page_script_can_close_its_block() -> None:
    for name in ("common.js", "detail.js", "universe.js", "flow.js", "boot.js"):
        assert "</script" not in (ASSETS / name).read_text(encoding="utf-8").lower(), name


# ---------------------------------------------------------------- M5.4: contrast, touch-ups (D-037 to D-039)


def test_flow_keeps_its_zoom_on_resize_without_a_listener() -> None:
    # M5.10 (D-045): the d3 zoom is relative to the box's top-left corner, so a resized window keeps
    # the user's zoom and pan with no resize handler (D-036 rule unchanged)
    flow = (ASSETS / "flow.js").read_text(encoding="utf-8")
    assert "'resize'" not in flow and "graphZoom(" in flow


def test_one_zoom_helper_serves_the_three_views() -> None:
    common = (ASSETS / "common.js").read_text(encoding="utf-8")
    for declaration in ("const ZOOM_EXTENT = ", "function zoomOn(", "function graphZoom("):
        assert common.count(declaration) == 1, declaration
    for event in ("gesturestart", "gesturechange", "gestureend"):  # Safari's trackpad pinch
        assert common.count(f"'{event}.gesture'") == 1, event
    for name in ("universe.js", "flow.js", "detail.js", "boot.js"):
        script = (ASSETS / name).read_text(encoding="utf-8")
        assert "d3.zoom()" not in script or name == "universe.js", name
        assert "gesture" not in script and "scaleExtent([" not in script, name
    assert "zoomOn(" in (ASSETS / "universe.js").read_text(encoding="utf-8")


def test_common_script_declares_the_m5_4_helpers() -> None:
    common = (ASSETS / "common.js").read_text(encoding="utf-8")
    for declaration in ("const CONTRAST = ", "const THEME = ", "const num = ", "const tableDesc = "):
        assert common.count(declaration) == 1, declaration
    for name in ("universe.js", "flow.js", "detail.js", "boot.js"):  # one helper each, no copy
        script = (ASSETS / name).read_text(encoding="utf-8")
        assert "toLocaleString" not in script and 'class="desc"' not in script, name


@pytest.mark.parametrize("name", ["common.js", "detail.js", "universe.js", "flow.js", "boot.js", "page.css"])
def test_no_asset_holds_an_invisible_space(name: str) -> None:
    text = (ASSETS / name).read_text(encoding="utf-8")
    assert "\u00a0" not in text and "\u202f" not in text, "write them as \\u00a0 / \\u202f escapes (D-039)"


# ---------------------------------------------------------------- M5.5: universe layout (D-040)


@pytest.mark.parametrize("offline", [False, True])
def test_flow_ranks_is_declared_once_in_common(offline: bool) -> None:
    page = render_page(DETAIL, UNIVERSE, merge_config({}, {}), offline=offline)
    assert page.count("function flowRanks(") == 1
    assert "function flowRanks(" in (ASSETS / "common.js").read_text(encoding="utf-8")
    for name in ("flow.js", "universe.js"):
        assert "function flowRanks(" not in (ASSETS / name).read_text(encoding="utf-8"), name
    assert len(re.findall(r"<script\b", page, re.IGNORECASE)) == len(re.findall(r"</script>", page, re.I))


@pytest.mark.parametrize("name", ["common.js", "detail.js", "universe.js", "flow.js", "boot.js"])
def test_the_page_strings_hold_none_of_the_words_d_084_retired(name: str) -> None:
    """M9.1 (D-084): the quoted strings of every script say lineage, lineage graph, dependency, table kind,
    "draw inside" and domain or layer, never the internal words (trajectory, flow, route, fold...)."""
    text = re.sub(r"(?m)^\s*//.*$|\s//\s.*$", "", (ASSETS / name).read_text(encoding="utf-8"))  # comments
    literals = re.findall(r"'(?:[^'\\\n]|\\.)*'|`(?:[^`\\]|\\.)*`", text)
    # selectors, CSS classes and the stored keys (D-013) keep the internal words
    shown = [s for s in literals if not s.startswith(("'#", "'.", "'dbtscope-"))]
    old = re.compile(
        r"Trajector|Trajectoire|\bFlow\b|\bFlux\b|Routes (between|entre)|constellation|\bTypes\b|lignée|"
        r"Show all routes|Afficher toutes les routes|Tout afficher|\bFold|Replier|[Rr]epliée"
    )
    assert [s for s in shown if old.search(re.sub(r"\$\{[^}]*\}", "", s))] == []  # code in ${} is no wording


@pytest.mark.parametrize("name", ["common.js", "detail.js", "universe.js", "flow.js"])
def test_french_strings_put_a_narrow_space_before_semicolon_and_question_mark(name: str) -> None:
    """D-039: before `;`, `?` and `!` French strings write the narrow no-break space escape (never U+00A0)."""
    text = (ASSETS / name).read_text(encoding="utf-8")
    assert not re.search(r"\\u00a0[;?!]", text)
