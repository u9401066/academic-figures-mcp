from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from src.application.edit_figure import EditFigureRequest, EditFigureUseCase
from src.domain.entities import GenerationResult
from src.domain.exceptions import ImageNotFoundError

if TYPE_CHECKING:
    from pathlib import Path


class StubGenerator:
    def __init__(self, result: GenerationResult) -> None:
        self._result = result
        self.calls: list[tuple[Path, str]] = []

    def generate(self, prompt: str, **_: object) -> GenerationResult:
        raise AssertionError(f"generate should not run: {prompt}")

    def edit(self, image_path: Path, instruction: str, **_: object) -> GenerationResult:
        self.calls.append((image_path, instruction))
        return self._result


def test_edit_figure_saves_default_edited_output(tmp_path: Path) -> None:
    image_path = tmp_path / "figure.png"
    image_path.write_bytes(b"source")
    generator = StubGenerator(
        GenerationResult(
            image_bytes=b"edited-image",
            text="Updated labels",
            model="stub-edit-model",
            elapsed_seconds=1.25,
        )
    )
    use_case = EditFigureUseCase(generator=generator)

    result = use_case.execute(
        EditFigureRequest(image_path=str(image_path), feedback="Make the labels larger")
    )

    expected_output = tmp_path / "figure_edited.png"
    assert result["status"] == "ok"
    assert result["output_path"] == str(expected_output)
    assert expected_output.read_bytes() == b"edited-image"
    assert result["model"] == "stub-edit-model"
    assert result["image_size_bytes"] == len(b"edited-image")
    assert generator.calls == [(image_path, "Make the labels larger")]


def test_edit_figure_reports_failed_edits(tmp_path: Path) -> None:
    image_path = tmp_path / "figure.png"
    image_path.write_bytes(b"source")
    generator = StubGenerator(
        GenerationResult(error="provider failed", model="stub-edit-model", elapsed_seconds=0.5)
    )
    use_case = EditFigureUseCase(generator=generator)

    result = use_case.execute(
        EditFigureRequest(image_path=str(image_path), feedback="Make the labels larger")
    )

    assert result == {
        "status": "edit_failed",
        "image_path": str(image_path),
        "error": "provider failed",
        "elapsed_seconds": 0.5,
    }


def test_edit_figure_raises_for_missing_image(tmp_path: Path) -> None:
    use_case = EditFigureUseCase(
        generator=StubGenerator(GenerationResult(image_bytes=b"edited-image"))
    )

    with pytest.raises(ImageNotFoundError, match="Image not found"):
        use_case.execute(
            EditFigureRequest(
                image_path=str(tmp_path / "missing.png"),
                feedback="Make the labels larger",
            )
        )


def test_edit_figure_normalizes_output_extension_to_match_media_type(tmp_path: Path) -> None:
    image_path = tmp_path / "figure.png"
    image_path.write_bytes(b"source")
    generator = StubGenerator(
        GenerationResult(
            image_bytes=b"\xff\xd8\xff\xe0edited-jpeg",
            media_type="image/jpeg",
            model="stub-edit-model",
            elapsed_seconds=0.75,
        )
    )
    use_case = EditFigureUseCase(generator=generator)

    result = use_case.execute(
        EditFigureRequest(
            image_path=str(image_path),
            feedback="Make the labels larger",
            output_path=str(tmp_path / "custom-name.png"),
        )
    )

    expected_output = tmp_path / "custom-name.jpg"
    assert result["status"] == "ok"
    assert result["output_path"] == str(expected_output)
    assert expected_output.read_bytes() == b"\xff\xd8\xff\xe0edited-jpeg"
