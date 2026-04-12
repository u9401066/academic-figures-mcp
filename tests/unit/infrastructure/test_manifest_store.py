from __future__ import annotations

import os
import time
from typing import TYPE_CHECKING

import pytest

from src.domain.entities import GenerationManifest
from src.domain.exceptions import ManifestNotFoundError
from src.infrastructure.manifest_store import FileManifestStore

if TYPE_CHECKING:
    from pathlib import Path


def _sample_manifest(manifest_id: str, output_path: Path) -> GenerationManifest:
    return GenerationManifest(
        manifest_id=manifest_id,
        asset_kind="academic_figure",
        figure_type="infographic",
        language="en",
        output_size="1024x1536",
        render_route_requested="image_generation",
        render_route_used="image_generation",
        prompt="prompt-blocks",
        prompt_base="prompt-base",
        planned_payload={"asset_kind": "academic_figure"},
        target_journal="Nature",
        journal_profile={"id": "nature_portfolio"},
        source_context={"pmid": "123"},
        output_path=str(output_path),
        model="stub-model",
        provider="google",
        generation_contract="planned_payload",
        warnings=["test-warning"],
    )


def test_file_manifest_store_saves_and_loads(tmp_path: Path) -> None:
    store = FileManifestStore(root_dir=str(tmp_path))
    manifest = _sample_manifest("manifest-1", output_path=tmp_path / "out.png")

    store.save(manifest)
    loaded = store.load("manifest-1")

    assert loaded.manifest_id == "manifest-1"
    assert loaded.journal_profile == {"id": "nature_portfolio"}
    assert loaded.prompt_base == "prompt-base"
    assert loaded.warnings == ["test-warning"]


def test_file_manifest_store_lists_latest_first(tmp_path: Path) -> None:
    store = FileManifestStore(root_dir=str(tmp_path))
    first = _sample_manifest("first", output_path=tmp_path / "first.png")
    second = _sample_manifest("second", output_path=tmp_path / "second.png")

    store.save(first)
    time.sleep(0.01)
    store.save(second)

    listed = store.list(limit=10)
    ids = [item.manifest_id for item in listed]
    assert ids[0] == "second"
    assert ids[1] == "first"


def test_file_manifest_store_raises_on_missing_manifest(tmp_path: Path) -> None:
    store = FileManifestStore(root_dir=str(tmp_path))

    with pytest.raises(ManifestNotFoundError):
        store.load("missing-id")


def test_file_manifest_store_skips_unreadable_files(tmp_path: Path) -> None:
    store = FileManifestStore(root_dir=str(tmp_path))
    good = _sample_manifest("good", output_path=tmp_path / "good.png")
    store.save(good)

    bad_path = tmp_path / "bad.json"
    bad_path.write_text("{not-json}", encoding="utf-8")
    os.utime(bad_path, (time.time(), time.time() + 1))

    listed = store.list(limit=5)
    assert any(item.manifest_id == "good" for item in listed)
