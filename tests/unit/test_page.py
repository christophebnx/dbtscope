from conftest import page_data

from dbtscope.domain.config import merge_config
from dbtscope.render.page import render_page

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
