"""Use case: evaluate a figure against the 8-domain quality checklist."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any

from src.application.contracts import (
    ApplicationErrorCategory,
    ApplicationStatus,
    serialize_error_contract,
    serialize_generation_result_contract,
)
from src.domain.exceptions import ImageNotFoundError
from src.domain.value_objects import EVAL_DOMAINS

if TYPE_CHECKING:
    from src.domain.interfaces import FigureEvaluator


@dataclass
class EvaluateFigureRequest:
    image_path: str
    figure_type: str = "infographic"
    reference_pmid: str | None = None


class EvaluateFigureUseCase:
    def __init__(self, evaluator: FigureEvaluator) -> None:
        self._evaluator = evaluator

    def execute(self, req: EvaluateFigureRequest) -> dict[str, Any]:
        img = Path(req.image_path)
        if not img.exists():
            raise ImageNotFoundError(f"Image not found: {req.image_path}")

        eval_prompt = (
            f"Evaluate this {req.figure_type} academic figure on the following 8 domains. "
            "For each domain give a score 1-5 and a one-line justification. "
            "Then give an overall score and list critical issues.\n\n"
            "Domains:\n" + "\n".join(f"- {d}" for d in EVAL_DOMAINS)
        )
        if req.reference_pmid:
            eval_prompt += f"\n\nReference paper: PMID {req.reference_pmid}"

        result = self._evaluator.evaluate(image_path=img, instruction=eval_prompt)

        payload: dict[str, Any] = {
            "status": (
                ApplicationStatus.OK.value if result.succeeded else ApplicationStatus.ERROR.value
            ),
            "image_path": str(img),
            "figure_type": req.figure_type,
            "reference_pmid": req.reference_pmid,
            "domains": list(EVAL_DOMAINS),
            "evaluation_text": result.text,
            "model": result.model,
            "elapsed_seconds": result.elapsed_seconds,
            "error": result.error if result.error else None,
        }
        if not result.succeeded:
            payload.update(
                serialize_error_contract(
                    status=ApplicationStatus.ERROR,
                    category=ApplicationErrorCategory.GENERATION_RESULT,
                )
            )
        payload.update(serialize_generation_result_contract(result))
        return payload
