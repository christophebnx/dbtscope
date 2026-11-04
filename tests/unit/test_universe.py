from dbtscope.domain.config import merge_config
from dbtscope.domain.model import Project
from dbtscope.domain.universe import UNRANKED, flow_rank, universe_data
from dbtscope.storage.project_files import read_preset


def test_domains_layers_and_kinds(shop: Project) -> None:
    file_config = {
        "domains": [
            {"key": "sales_team", "label": "Sales", "color": "#123456", "match": ["fct_orders"]},
            {"key": "returns", "match": ["fct_returns"]},
        ],
        "universe": {"hidden_kinds": ["source"]},
    }
    data = universe_data(shop, merge_config(read_preset("star_schema"), file_config))

    by_name = {n["name"]: n for n in data["nodes"]}
    assert set(by_name) == {
        "dim_customer",
        "dim_product",
        "fct_orders",
        "fct_returns",
        "stg_orders",
        "orders",
    }
    # dbt group, then meta.domain, then `domains` rules, then group_by (folder for this preset)
    assert by_name["dim_customer"]["domain"] == "sales_team"
    assert by_name["dim_product"]["domain"] == "products"
    assert by_name["fct_orders"]["domain"] == "sales_team"
    assert by_name["fct_returns"]["domain"] == "returns"
    assert by_name["stg_orders"]["domain"] == "staging"
    domains = {d["key"]: d for d in data["domains"]}
    assert domains["sales_team"] == {
        "key": "sales_team",
        "label": "Sales",
        "color": "#123456",
        "owner": "Ana",
    }
    assert domains["returns"]["color"].startswith("#")

    # default layers: sources first, then folders ordered along the flow
    assert [layer["key"] for layer in data["layers"]] == ["sources", "staging", "catalog", "sales"]
    assert by_name["orders"]["layer"] == "sources" and by_name["orders"]["kind"] == "source"
    assert by_name["stg_orders"]["kind"] == "other"
    assert data["defaults"] == {"links": "both", "detail": "names", "hiddenKinds": ["source"]}

    index = {n["name"]: i for i, n in enumerate(data["nodes"])}
    assert [index["stg_orders"], index["orders"]] in data["lineage"]
    assert [index["fct_orders"], index["dim_customer"]] in data["relations"]


def test_configured_layers(shop: Project) -> None:
    layers = [
        {"key": "raw", "label": "Raw", "match": ["type:source", "stg_*"]},
        {"key": "marts", "label": "Marts", "match": ["fct_*"]},
    ]
    data = universe_data(shop, merge_config({}, {"layers": layers}))
    assert [layer["key"] for layer in data["layers"]] == ["raw", "marts", "other"]
    assert {n["name"]: n["layer"] for n in data["nodes"]}["dim_customer"] == "other"


def test_tables_without_domain_come_last(shop: Project) -> None:
    data = universe_data(shop, merge_config({}, {"group_by": "none", "language": "fr"}))
    assert data["domains"][-1] == {"key": "", "label": "Hors domaine", "color": "#8a94a6", "owner": ""}


def test_flow_rank() -> None:
    assert flow_rank("sources") < flow_rank("staging") < flow_rank("int_dwh") < flow_rank("marts")
    assert flow_rank("misc") == UNRANKED
