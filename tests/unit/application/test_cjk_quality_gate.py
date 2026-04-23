"""Tests for CJK text policy, quality gate, and model escalation."""

from __future__ import annotations

from typing import cast

from src.application.plan_figure import (
    PlanFigureRequest,
    PlanFigureUseCase,
    _recommend_render_route,
)
from src.domain.entities import Paper
from src.domain.interfaces import MetadataFetcher, PromptBuilder
from src.domain.value_objects import (
    CJK_LANGUAGES,
    CJKTextPolicy,
)

# ── Domain value objects ─────────────────────────────────────


class TestCJKTextPolicy:
    def test_is_cjk_for_zh_tw(self) -> None:
        policy = CJKTextPolicy(language="zh-TW")
        assert policy.is_cjk is True

    def test_is_cjk_for_en(self) -> None:
        policy = CJKTextPolicy(language="en")
        assert policy.is_cjk is False

    def test_all_cjk_languages_detected(self) -> None:
        for lang in CJK_LANGUAGES:
            assert CJKTextPolicy(language=lang).is_cjk is True

    def test_text_heavy_with_labels(self) -> None:
        policy = CJKTextPolicy(language="zh-TW", expected_labels=("標題", "副標題"))
        assert policy.is_text_heavy is True

    def test_not_text_heavy_with_single_label(self) -> None:
        policy = CJKTextPolicy(language="zh-TW", expected_labels=("標題",))
        assert policy.is_text_heavy is False

    def test_recommend_pro_model_for_cjk_text_heavy(self) -> None:
        policy = CJKTextPolicy(
            language="zh-TW", expected_labels=("急性冠心症", "處置流程", "緊急處理")
        )
        assert policy.recommend_pro_model is True
        assert policy.recommend_vector_route is True

    def test_no_pro_model_for_english(self) -> None:
        policy = CJKTextPolicy(language="en", expected_labels=("Title", "Subtitle", "Footer"))
        assert policy.recommend_pro_model is False

    def test_needs_exact_text_block(self) -> None:
        policy = CJKTextPolicy(language="zh-TW", expected_labels=("急性冠心症",))
        assert policy.needs_exact_text_block is True

    def test_no_exact_text_block_without_labels(self) -> None:
        policy = CJKTextPolicy(language="zh-TW")
        assert policy.needs_exact_text_block is False


# ── Render route escalation for CJK ─────────────────────────


class TestCJKRouteEscalation:
    def test_flowchart_zh_tw_gets_svg(self) -> None:
        route, _reason = _recommend_render_route(
            title="急性冠心症處置流程",
            abstract="臨床指引共識演算法",
            figure_type="flowchart",
            language="zh-TW",
        )
        assert route == "code_render_svg"

    def test_infographic_zh_tw_text_heavy_gets_svg(self) -> None:
        route, _reason = _recommend_render_route(
            title="臨床指引共識",
            abstract="guideline consensus recommendation workflow algorithm",
            figure_type="infographic",
            language="zh-TW",
        )
        assert route == "code_render_svg"

    def test_anatomical_zh_tw_stays_image_generation(self) -> None:
        route, _reason = _recommend_render_route(
            title="解剖學參考圖",
            abstract="Neural block anatomy cross-section",
            figure_type="anatomical",
            language="zh-TW",
        )
        assert route == "image_generation"

    def test_timeline_zh_cn_gets_svg(self) -> None:
        route, _reason = _recommend_render_route(
            title="治疗演变时间线",
            abstract="Historical treatment evolution",
            figure_type="timeline",
            language="zh-CN",
        )
        assert route == "code_render_svg"


# ── Planner CJK integration ─────────────────────────────────


class StubFetcher(MetadataFetcher):
    def fetch_paper(self, pmid: str) -> Paper:
        return Paper(
            pmid=pmid,
            title="急性冠心症處置流程共識",
            authors="Test Author",
            journal="Journal of Testing",
            abstract="Consensus guideline algorithm for acute coronary syndrome workflow.",
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
        labels_str = ",".join(expected_labels) if expected_labels else ""
        return f"prompt::{paper.pmid}::{figure_type}::{language}::{labels_str}"

    def inject_journal_requirements(
        self,
        prompt: str,
        *,
        target_journal: str | None = None,
        source_journal: str | None = None,
    ) -> tuple[str, dict[str, object] | None]:
        return prompt, None


class TestPlannerCJKIntegration:
    def test_plan_includes_cjk_policy(self) -> None:
        uc = PlanFigureUseCase(
            fetcher=StubFetcher(),
            prompt_builder=StubPromptBuilder(),
            provider_name="google",
        )
        result = uc.execute(
            PlanFigureRequest(
                pmid="12345678",
                language="zh-TW",
                expected_labels=["急性冠心症", "處置流程", "緊急處理"],
            )
        )

        cjk_info = cast("dict[str, object]", result["cjk_text_policy"])
        assert cjk_info["is_cjk"] is True
        assert cjk_info["recommend_pro_model"] is True
        assert cjk_info["recommend_vector_route"] is True

    def test_plan_includes_model_recommendation(self) -> None:
        uc = PlanFigureUseCase(
            fetcher=StubFetcher(),
            prompt_builder=StubPromptBuilder(),
            provider_name="google",
        )
        result = uc.execute(
            PlanFigureRequest(
                pmid="12345678",
                language="zh-TW",
                figure_type="mechanism",
                expected_labels=["藥物機制", "受體結合", "信號傳導"],
            )
        )

        assert result["model_recommendation"] == "high_fidelity"
        assert "CJK text" in str(result["model_recommendation_reason"])

    def test_plan_warns_when_svg_route_is_not_executable_yet(self) -> None:
        uc = PlanFigureUseCase(
            fetcher=StubFetcher(),
            prompt_builder=StubPromptBuilder(),
            provider_name="google",
        )
        result = uc.execute(
            PlanFigureRequest(
                pmid="12345678",
                figure_type="flowchart",
                language="zh-TW",
            )
        )

        payload = cast("dict[str, object]", result["planned_payload"])
        warnings = cast("list[str]", result["warnings"])

        assert result["render_route"] == "image_generation"
        assert payload["render_route"] == "image_generation"
        assert any("code_render_svg" in warning for warning in warnings)

    def test_plan_expected_labels_in_payload(self) -> None:
        uc = PlanFigureUseCase(
            fetcher=StubFetcher(),
            prompt_builder=StubPromptBuilder(),
            provider_name="google",
        )
        result = uc.execute(
            PlanFigureRequest(
                pmid="12345678",
                language="zh-TW",
                expected_labels=["急性冠心症"],
            )
        )

        payload = cast("dict[str, object]", result["planned_payload"])
        assert payload["expected_labels"] == ["急性冠心症"]

    def test_cjk_warning_in_output(self) -> None:
        uc = PlanFigureUseCase(
            fetcher=StubFetcher(),
            prompt_builder=StubPromptBuilder(),
            provider_name="google",
        )
        result = uc.execute(
            PlanFigureRequest(
                pmid="12345678",
                language="zh-TW",
            )
        )

        warnings = cast("list[str]", result["warnings"])
        assert any("CJK" in w for w in warnings)


# ── Validation normalizers ──────────────────────────────────


class TestNewValidators:
    def test_normalize_expected_labels(self) -> None:
        from src.presentation.validation import normalize_expected_labels

        assert normalize_expected_labels(None) is None
        assert normalize_expected_labels([]) is None
        assert normalize_expected_labels(["  "]) is None
        assert normalize_expected_labels(["急性冠心症", "  ", "處置流程"]) == [
            "急性冠心症",
            "處置流程",
        ]

    def test_normalize_instructions(self) -> None:
        from src.presentation.validation import normalize_instructions

        assert normalize_instructions(["fix label"]) == ["fix label"]
        assert normalize_instructions(["a", "  ", "b"]) == ["a", "b"]

    def test_normalize_instructions_rejects_empty(self) -> None:
        import pytest

        from src.domain.exceptions import ValidationError
        from src.presentation.validation import normalize_instructions

        with pytest.raises(ValidationError):
            normalize_instructions([])

    def test_normalize_instructions_rejects_too_many(self) -> None:
        import pytest

        from src.domain.exceptions import ValidationError
        from src.presentation.validation import normalize_instructions

        with pytest.raises(ValidationError):
            normalize_instructions([f"step {i}" for i in range(11)])
