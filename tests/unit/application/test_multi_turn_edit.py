from __future__ import annotations

from pathlib import Path

import pytest

from src.application.multi_turn_edit import MultiTurnEditRequest, MultiTurnEditUseCase
from src.domain.entities import GenerationErrorKind, GenerationResult, GenerationResultStatus
from src.domain.exceptions import ValidationError


class StubSession:
    def __init__(self, results: list[GenerationResult]) -> None:
        self._results = results
        self.instructions: list[str] = []

    def send(self, instruction: str) -> GenerationResult:
        self.instructions.append(instruction)
        return self._results.pop(0)


class StubGenerator:
    def __init__(self, first_result: GenerationResult, session: StubSession) -> None:
        self._first_result = first_result
        self._session = session
        self.edit_calls: list[tuple[Path, str]] = []

    def create_edit_session(self) -> StubSession:
        return self._session

    def edit(self, image_path: Path, instruction: str, **_: object) -> GenerationResult:
        self.edit_calls.append((image_path, instruction))
        return self._first_result


def test_multi_turn_edit_serializes_turn_and_final_contracts(tmp_path: Path) -> None:
    image_path = tmp_path / "figure.png"
    image_path.write_bytes(b"source")
    first = GenerationResult(
        image_bytes=b"first-image",
        model="stub-model",
        elapsed_seconds=0.4,
    )
    second = GenerationResult(
        text="provider warning",
        error="warning text",
        status=GenerationResultStatus.TEXT_READY,
        model="stub-model",
        elapsed_seconds=0.6,
    )
    third = GenerationResult(
        image_bytes=b"final-image",
        model="stub-model",
        elapsed_seconds=0.7,
    )
    session = StubSession([second, third])
    use_case = MultiTurnEditUseCase(generator=StubGenerator(first, session))

    result = use_case.execute(
        MultiTurnEditRequest(
            image_path=str(image_path),
            instructions=["first", "second", "third"],
        )
    )

    assert result["status"] == "ok"
    assert result["final_result_status"] == GenerationResultStatus.IMAGE_READY.value
    assert result["final_error_kind"] is None
    assert result["turns_executed"] == 3
    assert result["turns"][0]["result_status"] == GenerationResultStatus.IMAGE_READY.value
    assert result["turns"][1]["result_status"] == GenerationResultStatus.TEXT_READY.value
    assert result["turns"][2]["result_status"] == GenerationResultStatus.IMAGE_READY.value
    assert result["turns"][1]["error_kind"] is None
    assert Path(str(result["final_output_path"])).read_bytes() == b"final-image"
    assert result["total_elapsed_seconds"] == 1.7


def test_multi_turn_edit_preserves_failed_final_contract_when_no_image_is_produced(
    tmp_path: Path,
) -> None:
    image_path = tmp_path / "figure.png"
    image_path.write_bytes(b"source")
    first = GenerationResult(
        error="provider failed",
        error_kind=GenerationErrorKind.PERMANENT,
        elapsed_seconds=0.5,
    )
    session = StubSession([])
    use_case = MultiTurnEditUseCase(generator=StubGenerator(first, session))

    result = use_case.execute(
        MultiTurnEditRequest(
            image_path=str(image_path),
            instructions=["first"],
        )
    )

    assert result["final_result_status"] == GenerationResultStatus.FAILED.value
    assert result["final_error_kind"] == GenerationErrorKind.PERMANENT.value
    assert result["final_output_path"] is None


def test_multi_turn_edit_request_rejects_empty_instructions() -> None:
    with pytest.raises(ValidationError, match="instructions"):
        MultiTurnEditRequest(image_path="figure.png", instructions=[])


def test_multi_turn_edit_request_rejects_zero_max_turns() -> None:
    with pytest.raises(ValidationError, match="max_turns"):
        MultiTurnEditRequest(image_path="figure.png", instructions=["adjust labels"], max_turns=0)
