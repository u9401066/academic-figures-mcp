from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from src.application.evaluate_figure import EvaluateFigureRequest, EvaluateFigureUseCase
from src.domain.entities import GenerationErrorKind, GenerationResult, GenerationResultStatus
from src.domain.exceptions import ImageNotFoundError
from src.domain.value_objects import EVAL_DOMAINS

if TYPE_CHECKING:
    from pathlib import Path


class StubGenerator:
    def __init__(self, result: GenerationResult) -> None:
        self._result = result
        self.calls: list[tuple[Path, str]] = []

    def evaluate(self, image_path: Path, instruction: str, **_: object) -> GenerationResult:
        self.calls.append((image_path, instruction))
        return self._result


def test_evaluate_figure_builds_prompt_with_reference_pmid(tmp_path: Path) -> None:
    image_path = tmp_path / "figure.png"
    image_path.write_bytes(b"source")
    generator = StubGenerator(
        GenerationResult(
            text="Overall score: 4/5",
            model="stub-eval-model",
            elapsed_seconds=2.0,
        )
    )
    use_case = EvaluateFigureUseCase(evaluator=generator)

    result = use_case.execute(
        EvaluateFigureRequest(
            image_path=str(image_path),
            figure_type="infographic",
            reference_pmid="12345678",
        )
    )

    assert result["status"] == "ok"
    assert result["figure_type"] == "infographic"
    assert result["reference_pmid"] == "12345678"
    assert result["domains"] == EVAL_DOMAINS
    assert result["evaluation_text"] == "Overall score: 4/5"
    assert result["model"] == "stub-eval-model"
    assert result["error"] is None
    assert result["result_status"] == GenerationResultStatus.TEXT_READY.value
    assert result["error_kind"] is None

    instruction = generator.calls[0][1]
    assert "Evaluate this infographic academic figure" in instruction
    for domain in EVAL_DOMAINS:
        assert f"- {domain}" in instruction
    assert "Reference paper: PMID 12345678" in instruction


def test_evaluate_figure_surfaces_generator_error_text(tmp_path: Path) -> None:
    image_path = tmp_path / "figure.png"
    image_path.write_bytes(b"source")
    generator = StubGenerator(
        GenerationResult(
            text="partial evaluation",
            model="stub-eval-model",
            elapsed_seconds=0.75,
            error="provider warning",
        )
    )
    use_case = EvaluateFigureUseCase(evaluator=generator)

    result = use_case.execute(EvaluateFigureRequest(image_path=str(image_path)))

    assert result["status"] == "ok"
    assert result["error"] == "provider warning"
    assert result["evaluation_text"] == "partial evaluation"
    assert result["result_status"] == GenerationResultStatus.TEXT_READY.value
    assert result["error_kind"] is None


def test_evaluate_figure_marks_failed_result_without_text(tmp_path: Path) -> None:
    image_path = tmp_path / "figure.png"
    image_path.write_bytes(b"source")
    generator = StubGenerator(
        GenerationResult(
            model="stub-eval-model",
            elapsed_seconds=0.75,
            error="provider failed",
            error_kind=GenerationErrorKind.PERMANENT,
        )
    )
    use_case = EvaluateFigureUseCase(evaluator=generator)

    result = use_case.execute(EvaluateFigureRequest(image_path=str(image_path)))

    assert result["status"] == "error"
    assert result["error_status"] == "error"
    assert result["error_category"] == "generation_result"
    assert result["result_status"] == GenerationResultStatus.FAILED.value
    assert result["error_kind"] == GenerationErrorKind.PERMANENT.value
    assert result["evaluation_text"] == ""
    assert result["error"] == "provider failed"


def test_evaluate_figure_raises_for_missing_image(tmp_path: Path) -> None:
    use_case = EvaluateFigureUseCase(evaluator=StubGenerator(GenerationResult(text="unused")))

    with pytest.raises(ImageNotFoundError, match="Image not found"):
        use_case.execute(EvaluateFigureRequest(image_path=str(tmp_path / "missing.png")))
