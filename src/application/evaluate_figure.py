"""Use case: evaluate a figure against the 8-domain quality checklist."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

from src.domain.exceptions import ImageNotFoundError
from src.domain.value_objects import EVAL_DOMAINS

if TYPE_CHECKING:
    from src.domain.interfaces import ImageGenerator


@dataclass
class EvaluateFigureRequest:
    image_path: str
    figure_type: str = "infographic"
    reference_pmid: str | None = None


class EvaluateFigureUseCase:
    def __init__(self, generator: ImageGenerator) -> None:
        self._generator = generator

    def execute(self, req: EvaluateFigureRequest) -> dict[str, object]:
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

        result = self._generator.edit(image_path=img, instruction=eval_prompt)

        return {
            "status": "ok",
            "image_path": str(img),
            "figure_type": req.figure_type,
            "reference_pmid": req.reference_pmid,
            "domains": list(EVAL_DOMAINS),
            "evaluation_text": result.text,
            "model": result.model,
            "elapsed_seconds": result.elapsed_seconds,
            "error": result.error if result.error else None,
        }
