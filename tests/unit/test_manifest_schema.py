from typing import get_args

import pytest
from conftest import model, relationships_test, source
from pydantic import ValidationError

from dbtscope.domain.manifest import NODE_TYPES
from dbtscope.domain.manifest_schema import ManifestFile, NodeHeader, RelationshipTest, SourceNode, TableNode


def test_a_model_entry_reads_the_fields_used() -> None:
    node = TableNode.model_validate(model("fct_orders", "sales", columns=["order_id"], group="g"))
    assert (node.unique_id, node.schema_name, node.package_name) == ("model.shop.fct_orders", "sales", "shop")
    assert node.columns is not None and node.columns["order_id"].data_type == "varchar"
    assert node.config is not None and node.config.meta == {}


def test_null_and_absent_optional_fields() -> None:
    node = TableNode.model_validate(
        {"unique_id": "u", "name": "n", "resource_type": "seed", "schema": None, "unknown": 1}
    )
    assert node.schema_name is None and node.columns is None and node.original_file_path == ""


def test_source_and_relationship_test() -> None:
    assert SourceNode.model_validate(source("orders")).source_name == "erp"
    with pytest.raises(ValidationError):
        SourceNode.model_validate({**source("orders"), "resource_type": "model"})
    test = RelationshipTest.model_validate(relationships_test("a", "b_id", "b", "id"))
    assert test.test_metadata.kwargs is not None and test.test_metadata.kwargs.field == "id"


def test_header_only_checks_the_dispatch_fields() -> None:
    header = NodeHeader.model_validate({"resource_type": "analysis", "name": 3, "columns": []})
    assert header.resource_type == "analysis" and header.test_metadata is None
    with pytest.raises(ValidationError):
        NodeHeader.model_validate({"resource_type": "test", "test_metadata": "x"})


def test_file_keeps_nodes_as_mappings_and_ignores_other_keys() -> None:
    parsed = ManifestFile.model_validate({"nodes": {"a": {"x": 1}}, "exposures": {"e": 1}})
    assert parsed.nodes == {"a": {"x": 1}} and parsed.sources == {} and parsed.metadata is None


def test_input_models_are_immutable() -> None:
    node = TableNode.model_validate(model("x"))
    with pytest.raises(ValidationError):
        node.name = "y"  # type: ignore[misc]


def test_drawn_node_types_are_the_table_node_types() -> None:
    assert set(get_args(TableNode.model_fields["resource_type"].annotation)) == NODE_TYPES
    assert {"model", "seed", "snapshot"} == NODE_TYPES
