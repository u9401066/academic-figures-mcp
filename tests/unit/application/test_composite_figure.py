from __future__ import annotations

import pytest

from src.application.composite_figure import CompositeFigureRequest, CompositeFigureUseCase
from src.domain.exceptions import ValidationError


class StubComposer:
    def __init__(self) -> None:
        self.calls: list[dict[str, object]] = []

    def compose(
        self,
        panels: list[dict[str, str]],
        *,
        title: str,
        caption: str,
        citation: str,
        output_path: str | None = None,
    ) -> dict[str, object]:
        self.calls.append(
            {
                "panels": panels,
                "title": title,
                "caption": caption,
                "citation": citation,
                "output_path": output_path,
            }
        )
        return {"status": "ok", "output_path": output_path or "composite.png"}


def test_composite_figure_delegates_to_composer() -> None:
    composer = StubComposer()
    use_case = CompositeFigureUseCase(composer=composer)

    result = use_case.execute(
        CompositeFigureRequest(
            panels=[{"image_path": "panel-a.png", "label": "A", "panel_type": "chart"}],
            title="Composite",
            caption="Caption",
            citation="PMID 123",
            output_path="out/composite.png",
        )
    )

    assert result == {"status": "ok", "output_path": "out/composite.png"}
    assert composer.calls == [
        {
            "panels": [
                {
                    "image_path": "panel-a.png",
                    "label": "A",
                    "panel_type": "chart",
                }
            ],
            "title": "Composite",
            "caption": "Caption",
            "citation": "PMID 123",
            "output_path": "out/composite.png",
        }
    ]


def test_composite_figure_rejects_empty_panels() -> None:
    use_case = CompositeFigureUseCase(composer=StubComposer())

    with pytest.raises(ValidationError, match="panels must contain at least one item"):
        use_case.execute(CompositeFigureRequest(panels=[], title="Composite"))
