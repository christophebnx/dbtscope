import re

import pytest
from conftest import page_data

from dbtscope.domain.config import merge_config
from dbtscope.render import page as page_module
from dbtscope.render.page import LIBRARIES, VENDOR, render_page

DETAIL = {"title": "x", "lang": "en", "grouped": False, "kinds": [], "relations": [], "entities": []}


def test_page_embeds_scripts_title_and_data() -> None:
    config = merge_config({}, {"title": "A & <B>", "view": "detail"})
    page = render_page(DETAIL, {"nodes": []}, config, {"format": "dbt-erd-layout"})
    assert "<title>A &amp; &lt;B></title>" in page
    assert "function startUniverse" in page and "function startDetail" in page
    assert "{{" not in page
    data = page_data(page)
    assert data["view"] == "detail" and data["layout"] == {"format": "dbt-erd-layout"}


def test_script_close_tag_is_escaped() -> None:
    entity = {
        "id": "a",
        "name": "a",
        "group": "",
        "kind": "other",
        "description": "</script><b>",
        "columns": [],
    }
    page = render_page({**DETAIL, "entities": [entity]}, {"nodes": []}, merge_config({}, {}))
    assert "</script><b>" not in page
    assert page_data(page)["detail"]["entities"][0]["description"] == "</script><b>"


def test_page_has_the_trajectory_mode() -> None:
    page = render_page(DETAIL, {"nodes": []}, merge_config({}, {}))
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
<script src="https://cdnjs.cloudflare.com/ajax/libs/viz.js/2.1.2/full.render.js"></script>
<script src="https://cdn.jsdelivr.net/npm/svg-pan-zoom@3.6.1/dist/svg-pan-zoom.min.js"></script>"""


def test_cdn_page_keeps_the_m1_script_tags() -> None:
    page = render_page(DETAIL, {"nodes": []}, merge_config({}, {}))
    after_data = page.split('id="data">', 1)[1].split("</script>\n", 1)[1]
    assert after_data.startswith(M1_SCRIPT_TAGS + "\n<script>\n// Detail view")
    assert page.count("<script src") == 4
    assert "/*! d3" not in page


def test_title_with_a_placeholder_is_not_substituted() -> None:
    page = render_page(DETAIL, {"nodes": []}, merge_config({}, {"title": "{{DATA}}"}))
    assert "<title>{{DATA}}</title>" in page
    assert page_data(page)["title"] == "{{DATA}}"


def _offline_page() -> str:
    return render_page(DETAIL, {"nodes": []}, merge_config({}, {}), offline=True)


def test_offline_page_embeds_every_library_in_order() -> None:
    page = _offline_page()
    assert not re.search(r"<script[^>]*\bsrc=", page, re.IGNORECASE)
    assert all(lib.url not in page for lib in LIBRARIES)
    assert len(re.findall(r"<script\b", page, re.IGNORECASE)) == len(re.findall(r"</script>", page, re.I))
    positions = [page.index(f"/*! {lib.name} {lib.version}, {lib.spdx}. Licence:") for lib in LIBRARIES[:2]]
    positions.append(page.index("Includes Graphviz 2.40.1, EPL-1.0. Licence:"))
    positions.append(page.index("/*! svg-pan-zoom 3.6.1, BSD-2-Clause. Licence:"))
    positions.append(page.index("// Detail view"))
    assert positions == sorted(positions)
    for lib in LIBRARIES:
        first = (VENDOR / lib.licence).read_text(encoding="utf-8").strip().splitlines()[0]
        assert first in page
    assert "Includes Expat 2.2.5, MIT. Licence:" in page
    assert page_data(page)["title"] == "dbt ERD"
    # minified libraries hold "{{" of their own: check no placeholder of the shell is left
    for name in ("STYLE", "SCRIPTS", "DETAIL_JS", "UNIVERSE_JS", "BOOT_JS", "TITLE", "DATA"):
        assert "{{" + name + "}}" not in page


def test_inlined_libraries_cannot_close_their_script(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(page_module, "_vendored", lambda name: 'var a = "</script>", b = "</SCRIPT"; /* */')
    page = _offline_page()
    assert '"<\\/script>"' in page and '"<\\/SCRIPT"' in page
    assert "* /" in page  # a licence cannot end the banner comment early
    assert len(re.findall(r"<script\b", page, re.IGNORECASE)) == len(re.findall(r"</script>", page, re.I))


def test_page_has_the_export_controls() -> None:
    page = render_page(DETAIL, {"nodes": []}, merge_config({}, {}))
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
