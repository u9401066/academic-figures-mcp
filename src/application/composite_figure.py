"""Use case: assemble a composite figure from pre-rendered panels."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from src.domain.exceptions import ValidationError

if TYPE_CHECKING:
    from src.domain.interfaces import FigureComposer


@dataclass
class CompositeFigureRequest:
    panels: list[dict[str, str]]
    title: str
    caption: str = ""
    citation: str = ""
    output_path: str | None = None


class CompositeFigureUseCase:
    def __init__(self, composer: FigureComposer) -> None:
        self._composer = composer

    def execute(self, req: CompositeFigureRequest) -> dict[str, object]:
        if not req.panels:
            raise ValidationError("panels must contain at least one item")

        return self._composer.compose(
            req.panels,
            title=req.title,
            caption=req.caption,
            citation=req.citation,
            output_path=req.output_path,
        )
