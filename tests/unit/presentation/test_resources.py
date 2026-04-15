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
