from __future__ import annotations

from typing import cast

import pytest

from src.application.plan_figure import PlanFigureRequest, PlanFigureUseCase
from src.domain.entities import Paper
from src.domain.exceptions import ValidationError
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
    def build_prompt(
        self,
        paper: Paper,
        figure_type: str,
        language: str,
        output_size: str,
        expected_labels: list[str] | None = None,
    ) -> str:
        source_marker = paper.pmid or paper.source_identifier or paper.title
        return f"prompt::{source_marker}::{figure_type}::{language}::{output_size}"

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


def test_plan_figure_carries_output_format_into_planned_payload() -> None:
    use_case = PlanFigureUseCase(
        fetcher=StubFetcher(),
        prompt_builder=StubPromptBuilder(),
        provider_name="google",
    )

    result = use_case.execute(PlanFigureRequest(pmid="12345678", output_format="webp"))

    planned_payload = cast("dict[str, object]", result["planned_payload"])
    assert result["output_format"] == "webp"
    assert planned_payload["output_format"] == "webp"


def test_plan_figure_reconciles_non_executable_route_to_executable_payload() -> None:
    use_case = PlanFigureUseCase(
        fetcher=StubFetcher(),
        prompt_builder=StubPromptBuilder(),
        provider_name="google",
    )

    result = use_case.execute(
        PlanFigureRequest(
            pmid="12345678",
            figure_type="flowchart",
            language="en",
        )
    )

    planned_payload = cast("dict[str, object]", result["planned_payload"])
    warnings = cast("list[str]", result["warnings"])
    assert result["render_route"] == "image_generation"
    assert planned_payload["render_route"] == "image_generation"
    assert any("not executable yet" in warning for warning in warnings)


def test_plan_request_rejects_conflicting_source_modes() -> None:
    with pytest.raises(ValidationError, match="Provide either pmid or source_title, not both"):
        PlanFigureRequest(pmid="12345678", source_title="Repo brief")

    with pytest.raises(ValidationError, match=r"source_\* fields are only supported"):
        PlanFigureRequest(
            pmid="12345678",
            source_identifier="github.com/example/hhrag",
        )


def test_plan_figure_accepts_generic_repo_brief_without_fetching() -> None:
    class FailingFetcher(MetadataFetcher):
        def fetch_paper(self, pmid: str) -> Paper:
            raise AssertionError("fetcher should not be called for generic sources")

    use_case = PlanFigureUseCase(
        fetcher=FailingFetcher(),
        prompt_builder=StubPromptBuilder(),
        provider_name="google",
    )

    result = use_case.execute(
        PlanFigureRequest(
            source_title="HyperHierarchicalRAG repository overview",
            source_summary=(
                "A repository that explains hierarchical retrieval and agent workflow design."
            ),
            source_kind="repo",
            source_identifier="github.com/example/hhrag",
        )
    )

    planned_payload = cast("dict[str, object]", result["planned_payload"])
    source_context = cast("dict[str, object]", planned_payload["source_context"])

    assert result["pmid"] is None
    assert result["source_kind"] == "repo"
    assert planned_payload["asset_kind"] == "repository_figure"
    assert source_context["source_kind"] == "repo"
    assert source_context["source_identifier"] == "github.com/example/hhrag"
    assert planned_payload["references"] == ["Repository github.com/example/hhrag"]
    assert "github.com/example/hhrag" in str(result["prompt_preview"])
