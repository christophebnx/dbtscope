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
