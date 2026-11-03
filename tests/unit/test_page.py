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
