"""Inventory resource — tools list stays in sync with tools.py."""

from __future__ import annotations

import json

from src.presentation.resources import inventory_resource


def test_inventory_lists_all_registered_tools() -> None:
    """Every @mcp.tool function in tools.py should appear in the inventory."""
    expected_tools = {
        "plan_figure",
        "generate_figure",
        "edit_figure",
        "prepare_publication_image",
        "evaluate_figure",
        "batch_generate",
        "composite_figure",
        "get_manifest_detail",
        "record_host_review",
        "verify_figure",
        "multi_turn_edit",
        "list_manifests",
        "replay_manifest",
        "retarget_journal",
    }
    inventory = json.loads(inventory_resource())
    actual_tools = set(inventory["tools"])
    assert actual_tools == expected_tools


def test_inventory_documents_typed_review_schema() -> None:
    inventory = json.loads(inventory_resource())

    review_contract = inventory["review_contract"]
    assert review_contract["manifest_detail_tool"] == "get_manifest_detail"
    assert "TypeScript interfaces" in review_contract["extension_type_mapping_guidance"]
    assert review_contract["typed_fields"]["quality_gate"] == [
        "route",
        "route_status",
        "review_route",
        "review_status",
        "passed",
    ]
    assert "review_timeline[].route_status" in review_contract["typed_fields"]["manifest_detail"]


def test_inventory_documents_typed_error_schema() -> None:
    inventory = json.loads(inventory_resource())

    error_contract = inventory["error_contract"]
    assert error_contract["typed_fields"] == ["error_status", "error_category", "error"]
    assert "generation_result" in error_contract["categories"]
    assert "TypeScript interfaces" in error_contract["extension_type_mapping_guidance"]


def test_inventory_documents_typed_aggregate_schema() -> None:
    inventory = json.loads(inventory_resource())

    aggregate_contract = inventory["aggregate_contract"]
    assert aggregate_contract["typed_fields"]["core"] == [
        "aggregate_kind",
        "aggregate_status",
        "item_count",
    ]
    assert aggregate_contract["typed_fields"]["batch_generate"] == [
        "total_count",
        "success_count",
        "failed_count",
    ]
    assert aggregate_contract["typed_fields"]["list_manifests"] == ["item_count"]
    assert aggregate_contract["kinds"] == ["batch_generate", "list_manifests"]
    assert "complete_partial_failure" in aggregate_contract["statuses"]
    assert "list_ready" in aggregate_contract["statuses"]
    assert "TypeScript interfaces" in aggregate_contract["extension_type_mapping_guidance"]
