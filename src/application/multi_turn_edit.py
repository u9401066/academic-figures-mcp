"""Use case: multi-turn edit session for iterative figure refinement."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any, Protocol

from src.application.contracts import (
    ApplicationStatus,
    prefix_contract,
    serialize_generation_result_contract,
)
from src.domain.exceptions import (
    ConfigurationError,
    ImageNotFoundError,
    ProviderCapabilityError,
    ValidationError,
)

if TYPE_CHECKING:
    from src.domain.entities import GenerationResult


class EditSession(Protocol):
    def send(self, instruction: str) -> GenerationResult: ...


class MultiTurnEditGenerator(Protocol):
    def create_edit_session(self) -> EditSession: ...

    def edit(
        self,
        image_path: Path,
        instruction: str,
        *,
        model: str | None = None,
    ) -> GenerationResult: ...


@dataclass
class MultiTurnEditRequest:
    image_path: str
    instructions: list[str]
    max_turns: int = 5

    def __post_init__(self) -> None:
        if self.max_turns < 1:
            raise ValidationError("max_turns must be at least 1")

        self.instructions = [
            instruction.strip() for instruction in self.instructions if instruction.strip()
        ]
        if not self.instructions:
            raise ValidationError("instructions must include at least one edit instruction")


class MultiTurnEditUseCase:
    """Iteratively refine a figure using a multi-turn chat session.

    Opens an edit session on the underlying adapter and sends each
    instruction turn-by-turn, preserving generation context between turns.
    Ideal for CJK label corrections where multiple passes may be needed.
    """

    def __init__(self, generator: MultiTurnEditGenerator) -> None:
        self._generator = generator

    def execute(self, req: MultiTurnEditRequest) -> dict[str, Any]:
        img = Path(req.image_path)
        if not img.exists():
            raise ImageNotFoundError(f"Image not found: {req.image_path}")

        # Check if multi-turn is supported
        create_session = getattr(self._generator, "create_edit_session", None)
        if create_session is None:
            raise ProviderCapabilityError("Multi-turn edit sessions require the Google provider.")

        try:
            session = create_session()
        except Exception as exc:
            raise ConfigurationError(f"Failed to create edit session: {exc}") from exc

        # First turn: send the image with the first instruction
        turns: list[dict[str, Any]] = []
        instructions = req.instructions[: req.max_turns]

        # Bootstrap the session with the image
        first_instruction = instructions[0]
        first_result = self._generator.edit(
            image_path=img,
            instruction=first_instruction,
        )
        turns.append(
            {
                "turn": 1,
                "instruction": first_instruction,
                "ok": first_result.ok,
                "text": first_result.text,
                "error": first_result.error,
                "elapsed_seconds": first_result.elapsed_seconds,
                **serialize_generation_result_contract(first_result),
            }
        )

        latest_result = first_result
        latest_bytes = first_result.image_bytes

        # Subsequent turns via the chat session
        for i, instruction in enumerate(instructions[1:], start=2):
            result = session.send(instruction)
            turns.append(
                {
                    "turn": i,
                    "instruction": instruction,
                    "ok": result.ok,
                    "text": result.text,
                    "error": result.error,
                    "elapsed_seconds": result.elapsed_seconds,
                    **serialize_generation_result_contract(result),
                }
            )
            if result.ok and result.image_bytes:
                latest_result = result
                latest_bytes = result.image_bytes

        # Save the final result
        output_path: str | None = None
        if latest_bytes:
            out_path = img.parent / f"{img.stem}_edited_multi{latest_result.file_extension}"
            out_path.write_bytes(latest_bytes)
            output_path = str(out_path)

        total_elapsed = 0.0
        for t in turns:
            val = t.get("elapsed_seconds", 0)
            if isinstance(val, (int, float)):
                total_elapsed += float(val)

        payload: dict[str, Any] = {
            "status": ApplicationStatus.OK.value,
            "turns_executed": len(turns),
            "turns": turns,
            "final_output_path": output_path,
            "final_model": latest_result.model,
            "total_elapsed_seconds": total_elapsed,
        }
        payload.update(
            prefix_contract(
                "final",
                serialize_generation_result_contract(latest_result),
            )
        )
        return payload
