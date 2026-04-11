from __future__ import annotations

from typing import cast

from src.application.plan_figure import PlanFigureRequest, PlanFigureUseCase
from src.domain.entities import Paper
from src.domain.interfaces import MetadataFetcher, PromptBuilder


class StubFetcher(MetadataFetcher):
    def fetch_paper(self, pmid: str) -> Paper:
        return Paper(
            pmid=pmid,
            title="Perioperative Airway Algorithm",
            authors="Example Author",
            journal="Journal of Testing",
            abstract="Consensus algorithm for perioperative airway rescue workflows.",
        )


class StubPromptBuilder(PromptBuilder):
    def build_prompt(self, paper: Paper, figure_type: str, language: str, output_size: str) -> str:
        return f"prompt::{paper.pmid}::{figure_type}::{language}::{output_size}"

    def inject_journal_requirements(
        self,
        prompt: str,
        *,
        target_journal: str | None = None,
        source_journal: str | None = None,
    ) -> tuple[str, dict[str, object] | None]:
        if target_journal == "Nature" or source_journal == "Nature":
            return (
                prompt + "::nature_profile",
                {
                    "id": "nature_portfolio",
                    "display_name": "Nature Portfolio",
                },
            )
        return prompt, None


def test_plan_figure_emits_reusable_planned_payload() -> None:
    use_case = PlanFigureUseCase(
        fetcher=StubFetcher(),
        prompt_builder=StubPromptBuilder(),
        provider_name="google",
    )

    result = use_case.execute(PlanFigureRequest(pmid="12345678"))

    planned_payload = result["planned_payload"]
    next_step = cast("dict[str, object]", result["next_step"])
    arguments = cast("dict[str, object]", next_step["arguments"])
    assert isinstance(planned_payload, dict)
    assert planned_payload["asset_kind"] == "academic_figure"
    assert planned_payload["source_context"]["pmid"] == "12345678"
    assert planned_payload["prompt_pack"]["prompt"] == result["prompt_preview"]
    assert arguments["planned_payload"] == planned_payload


def test_plan_figure_resolves_explicit_target_journal() -> None:
    use_case = PlanFigureUseCase(
        fetcher=StubFetcher(),
        prompt_builder=StubPromptBuilder(),
        provider_name="google",
    )

    result = use_case.execute(PlanFigureRequest(pmid="12345678", target_journal="Nature"))

    journal_profile = cast("dict[str, object]", result["journal_profile"])
    planned_payload = cast("dict[str, object]", result["planned_payload"])
    payload_profile = cast("dict[str, object]", planned_payload["journal_profile"])

    assert journal_profile["id"] == "nature_portfolio"
    assert payload_profile["id"] == "nature_portfolio"
    assert str(result["prompt_preview"]).endswith("::nature_profile")
