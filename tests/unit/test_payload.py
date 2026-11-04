import json

import pytest
from conftest import empty_universe
from pydantic import BaseModel, ValidationError

from dbtscope.domain.payload import (
    DetailEntity,
    DetailKind,
    DetailPayload,
    DetailRelation,
    PagePayload,
    UniverseDefaults,
    UniverseDomain,
    UniverseKind,
    UniverseLayer,
    UniverseNode,
    UniversePayload,
)

ENTITY = DetailEntity(
    id="model.shop.a", name="a", group="g", kind="other", description="d", columns=(("id", "int", True, ""),)
)
NODE = UniverseNode(
    id="model.shop.a", name="a", domain="d", layer="l", kind="k", desc="", cols=(("id", "int", 1),)
)
DETAIL = DetailPayload(
    title="t", lang="en", grouped=True,
    kinds=(DetailKind(key="k", label=None, color="#777777", bg="#efefef"),), entities=(ENTITY,),
    relations=(DetailRelation(child="a", parent="b", column="b_id"),),
)  # fmt: skip
UNIVERSE = UniversePayload(
    nodes=(NODE,), relations=((0, 0),), lineage=(),
    domains=(UniverseDomain(key="d", label="D", color="#000000", owner=""),),
    layers=(UniverseLayer(key="l", label=None),), kinds=(UniverseKind(key="k", label="K", color="#111111"),),
    defaults=UniverseDefaults(links="both", detail="names", hidden_kinds=("k",)),
)  # fmt: skip


def _json(model: BaseModel) -> str:
    """As render_page writes it."""
    return json.dumps(
        model.model_dump(mode="python", by_alias=True), ensure_ascii=False, separators=(",", ":")
    )


@pytest.mark.parametrize(
    ("model", "keys"),
    [
        (DETAIL, ["title", "lang", "grouped", "kinds", "entities", "relations"]),
        (DETAIL.kinds[0], ["key", "label", "color", "bg"]),
        (ENTITY, ["id", "name", "group", "kind", "description", "columns"]),
        (DETAIL.relations[0], ["child", "parent", "column"]),
        (UNIVERSE, ["nodes", "relations", "lineage", "domains", "layers", "kinds", "defaults"]),
        (NODE, ["id", "name", "domain", "layer", "kind", "desc", "cols"]),
        (UNIVERSE.domains[0], ["key", "label", "color", "owner"]),
        (UNIVERSE.layers[0], ["key", "label"]),
        (UNIVERSE.kinds[0], ["key", "label", "color"]),
        (UNIVERSE.defaults, ["links", "detail", "hiddenKinds"]),
    ],
)
def test_keys_dump_in_the_order_the_page_reads(model: BaseModel, keys: list[str]) -> None:
    assert list(json.loads(_json(model))) == keys


def test_positional_arrays_booleans_and_null_labels() -> None:
    assert '"columns":[["id","int",true,""]]' in _json(DETAIL)
    assert '"cols":[["id","int",1]]' in _json(UNIVERSE)
    assert '"relations":[[0,0]]' in _json(UNIVERSE)
    assert '"hiddenKinds":["k"]' in _json(UNIVERSE)
    assert '"label":null' in _json(DETAIL) and '"label":null' in _json(UNIVERSE)


def test_page_payload_wraps_both_views() -> None:
    page = PagePayload(
        title="t", lang="fr", view="detail", detail=DETAIL, universe=empty_universe(), layout={}
    )
    assert list(json.loads(_json(page))) == ["title", "lang", "view", "detail", "universe", "layout"]


def test_defaults_are_built_by_their_python_name_only() -> None:
    defaults = UniverseDefaults.model_validate({"links": "both", "detail": "all", "hidden_kinds": ["x"]})
    assert defaults.hidden_kinds == ("x",)
    with pytest.raises(ValidationError):
        UniverseDefaults.model_validate({"links": "both", "detail": "all", "hiddenKinds": ["x"]})


def test_payloads_are_closed_and_immutable() -> None:
    with pytest.raises(ValidationError):
        DetailRelation(child="a", parent="b", column="c", colour="red")  # type: ignore[call-arg]
    with pytest.raises(ValidationError):
        NODE.name = "b"  # type: ignore[misc]
    with pytest.raises(ValidationError):
        PagePayload(title="t", lang="de", view="detail", detail=DETAIL, universe=UNIVERSE, layout={})  # type: ignore[arg-type]
