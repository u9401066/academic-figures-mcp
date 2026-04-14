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
from src.infrastructure.gemini_adapter import GeminiImageVerifier
from src.infrastructure.prompt_engine import PromptEngine

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


# ── Prompt engine CJK block ─────────────────────────────────


class TestPromptEngineCJKBlock:
    def test_build_cjk_text_block_for_zh_tw(self) -> None:
        block = PromptEngine._build_cjk_text_block(
            language="zh-TW",
            expected_labels=["急性冠心症", "處置流程"],
        )
        assert "Block 8: CJK TEXT FIDELITY" in block
        assert "target_script: zh-TW" in block
        assert "「急性冠心症」" in block
        assert "「處置流程」" in block
        assert "Do NOT romanize" in block

    def test_no_cjk_block_for_english(self) -> None:
        block = PromptEngine._build_cjk_text_block(
            language="en",
            expected_labels=["Title"],
        )
        assert block == ""

    def test_cjk_block_without_labels(self) -> None:
        block = PromptEngine._build_cjk_text_block(
            language="zh-TW",
            expected_labels=[],
        )
        assert "No specific labels provided" in block

    def test_build_prompt_includes_cjk_block(self) -> None:
        engine = PromptEngine()
        paper = Paper(
            pmid="12345678",
            title="Test Paper",
            authors="Author",
            journal="Journal",
            abstract="Test abstract",
        )
        prompt = engine.build_prompt(
            paper=paper,
            figure_type="infographic",
            language="zh-TW",
            output_size="1024x1536",
            expected_labels=["急性冠心症", "治療流程"],
        )
        assert "Block 8: CJK TEXT FIDELITY" in prompt
        assert "「急性冠心症」" in prompt

    def test_build_prompt_no_cjk_block_for_english(self) -> None:
        engine = PromptEngine()
        paper = Paper(
            pmid="12345678",
            title="Test Paper",
            authors="Author",
            journal="Journal",
            abstract="Test abstract",
        )
        prompt = engine.build_prompt(
            paper=paper,
            figure_type="infographic",
            language="en",
            output_size="1024x1536",
            expected_labels=["Title", "Header"],
        )
        assert "Block 8" not in prompt


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


# ── Quality verdict parsing ─────────────────────────────────


class TestQualityVerdictParsing:
    def test_parse_passing_verdict(self) -> None:
        text = (
            "text_accuracy: 5 Excellent\n"
            "anatomy: 4 Good\n"
            "color: 5 Perfect\n"
            "layout: 4 Nice\n"
            "scientific_accuracy: 4 Correct\n"
            "legibility: 5 Clear\n"
            "visual_polish: 4 Polished\n"
            "citation: 5 Present\n"
        )
        verdict = GeminiImageVerifier._parse_verdict(text, expected_labels=[])
        assert verdict.passed is True
        assert verdict.total_score == 36.0
        assert verdict.domain_scores["text_accuracy"] == 5.0

    def test_parse_failing_verdict(self) -> None:
        text = (
            "text_accuracy: 2 Poor\n"
            "anatomy: 2 Inaccurate\n"
            "color: 2 Bad\n"
            "layout: 2 Messy\n"
            "scientific_accuracy: 2 Wrong\n"
            "legibility: 2 Unreadable\n"
            "visual_polish: 2 Rough\n"
            "citation: 2 Missing\n"
            "CRITICAL: All text is garbled."
        )
        verdict = GeminiImageVerifier._parse_verdict(text, expected_labels=[])
        assert verdict.passed is False
        assert len(verdict.critical_issues) > 0

    def test_parse_missing_labels(self) -> None:
        text = (
            "text_accuracy: 4 OK\n"
            "anatomy: 4 OK\n"
            "color: 4 OK\n"
            "layout: 4 OK\n"
            "scientific_accuracy: 4 OK\n"
            "legibility: 4 OK\n"
            "visual_polish: 4 OK\n"
            "citation: 4 OK\n"
            "Label check:\n"
            "急性冠心症: FOUND_EXACT\n"
            "處置流程: MISSING in the figure\n"
        )
        verdict = GeminiImageVerifier._parse_verdict(
            text, expected_labels=["急性冠心症", "處置流程"]
        )
        assert verdict.text_verification_passed is False
        assert "處置流程" in verdict.missing_labels

    def test_verdict_passes_when_all_labels_found(self) -> None:
        text = (
            "text_accuracy: 4 OK\n"
            "anatomy: 4 OK\n"
            "color: 4 OK\n"
            "layout: 4 OK\n"
            "scientific_accuracy: 4 OK\n"
            "legibility: 4 OK\n"
            "visual_polish: 4 OK\n"
            "citation: 4 OK\n"
            "All labels found correctly."
        )
        verdict = GeminiImageVerifier._parse_verdict(
            text, expected_labels=["急性冠心症", "處置流程"]
        )
        assert verdict.text_verification_passed is True
        assert len(verdict.missing_labels) == 0


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
