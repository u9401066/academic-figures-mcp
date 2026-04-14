"""7-block prompt engine — implements domain PromptBuilder."""

from __future__ import annotations

import re
from pathlib import Path
from typing import TYPE_CHECKING, Any

from src.domain.interfaces import PromptBuilder
from src.infrastructure.journal_registry import JournalRegistry

if TYPE_CHECKING:
    from src.domain.entities import Paper

_FIGURE_TYPE_TO_TEMPLATE: dict[str, str] = {
    "flowchart": "clinical_guideline_flowchart",
    "mechanism": "drug_mechanism",
    "comparison": "trial_comparison",
    "infographic": "general_infographic",
    "timeline": "timeline_evolution",
    "anatomical": "anatomical_reference",
    "data_visualization": "data_chart",
    "statistical": "data_chart",
}


class PromptEngine(PromptBuilder):
    """Loads reference templates and builds 7-block prompts for Gemini."""

    def __init__(self, template_dir: str | None = None) -> None:
        if template_dir is None:
            template_dir = str(Path(__file__).parent.parent.parent / "templates")
        self.template_dir = Path(template_dir)
        self._templates: dict[str, str] = {}
        self._color_standards: str | None = None
        self._journal_standards: str | None = None
        self._journal_registry = JournalRegistry(self.template_dir / "journal-profiles.yaml")
        self._load_all()

    def build_prompt(
        self,
        paper: Paper,
        figure_type: str,
        language: str,
        output_size: str,
    ) -> str:
        block1 = (
            f"## Block 1: TITLE & PURPOSE\n"
            f"title: '{paper.title}'\n"
            f"purpose: Academic medical figure visualizing key findings "
            f"from PMID {paper.pmid}"
        )
        block2 = self._get_layout(figure_type)
        block3 = (
            f"## Block 3: ELEMENTS\n"
            f"paper_title: '{paper.title}'\n"
            f"abstract_length: {len(paper.abstract)} chars"
        )
        block4 = self._get_color_scheme(figure_type)
        lang_text = f"Traditional Chinese ({language})" if language == "zh-TW" else language
        block5 = (
            f"## Block 5: TEXT\n"
            f"language: {lang_text}\n"
            f"citation: '{paper.authors} · {paper.journal}'\n"
            f"pmid: PMID {paper.pmid}"
        )
        block6 = self._get_style(figure_type)
        block7 = f"## Block 7: SIZE\ncanvas: {output_size}"

        return "\n\n".join([block1, block2, block3, block4, block5, block6, block7])

    def inject_journal_requirements(
        self,
        prompt: str,
        *,
        target_journal: str | None = None,
        source_journal: str | None = None,
    ) -> tuple[str, dict[str, object] | None]:
        profile = self._journal_registry.resolve_profile(
            target_journal=target_journal,
            source_journal=source_journal,
        )
        if profile is None:
            return prompt, None
        if "## Journal Profile" in prompt:
            return prompt, profile
        journal_block = self._format_journal_profile_block(profile)
        return f"{prompt}\n\n{journal_block}", profile

    # ── Loading helpers ─────────────────────────────────────

    def _load_all(self) -> None:
        try:
            self._load_templates()
            self._load_color_standards()
            self._load_journal_standards()
        except (OSError, UnicodeError):
            pass  # templates are optional — prompts degrade gracefully

    def _load_templates(self) -> None:
        prompt_file = self.template_dir / "prompt-templates.md"
        if not prompt_file.exists():
            return
        content = prompt_file.read_text(encoding="utf-8")
        templates = re.split(r"###\s*Template\s*\d+:", content)
        for tpl in templates[1:]:
            lines = tpl.strip().split("\n")
            name = lines[0].strip() if lines else "unknown"
            template_name = name.split("(")[0].split("-")[0].strip()
            template_name = template_name.lower().replace(" ", "_")
            self._templates[template_name] = content

    def _load_color_standards(self) -> None:
        p = self.template_dir / "anatomy-color-standards.md"
        if p.exists():
            self._color_standards = p.read_text(encoding="utf-8")

    def _load_journal_standards(self) -> None:
        p = self.template_dir / "journal-figure-standards.md"
        if p.exists():
            self._journal_standards = p.read_text(encoding="utf-8")

    def _format_journal_profile_block(self, profile: dict[str, Any]) -> str:
        display_name = self._as_text(profile.get("display_name")) or self._as_text(
            profile.get("id")
        )
        lines = [
            "## Journal Profile",
            f"profile: {display_name}",
        ]

        matched_on = self._as_text(profile.get("matched_on"))
        matched_by = self._as_text(profile.get("matched_by"))
        if matched_on:
            lines.append(f"matched_on: {matched_on}")
        if matched_by:
            lines.append(f"matched_by: {matched_by}")

        layout_constraints = self._format_mapping(profile.get("dimensions_mm"))
        if layout_constraints:
            lines.append(f"layout_constraints: {layout_constraints}")

        typography_constraints = self._format_mapping(profile.get("typography"))
        if typography_constraints:
            lines.append(f"typography_constraints: {typography_constraints}")

        resolution_constraints = self._format_mapping(profile.get("resolution"))
        if resolution_constraints:
            lines.append(f"resolution_constraints: {resolution_constraints}")

        format_constraints = self._format_mapping(profile.get("formats"))
        if format_constraints:
            lines.append(f"format_constraints: {format_constraints}")

        display_item_limits = self._format_mapping(profile.get("display_item_limits"))
        if display_item_limits:
            lines.append(f"display_item_limits: {display_item_limits}")

        required_rules = self._format_list(profile.get("required_rules"))
        if required_rules:
            lines.append(f"required_rules: {required_rules}")

        avoid_rules = self._format_list(profile.get("avoid_rules"))
        if avoid_rules:
            lines.append(f"avoid_rules: {avoid_rules}")

        prompt_injection = profile.get("prompt_injection")
        if isinstance(prompt_injection, dict):
            positive = self._format_list(prompt_injection.get("positive"))
            negative = self._format_list(prompt_injection.get("negative"))
            if positive:
                lines.append(f"prompt_positive: {positive}")
            if negative:
                lines.append(f"prompt_negative: {negative}")

        return "\n".join(lines)

    @classmethod
    def _format_mapping(cls, value: object) -> str:
        if not isinstance(value, dict):
            return ""

        parts: list[str] = []
        for key, raw_value in value.items():
            key_text = key.replace("_", " ")
            if isinstance(raw_value, list):
                value_text = cls._format_list(raw_value)
            elif isinstance(raw_value, dict):
                value_text = cls._format_mapping(raw_value)
            elif isinstance(raw_value, str):
                value_text = raw_value.strip()
            elif isinstance(raw_value, (int, float, bool)):
                value_text = str(raw_value)
            else:
                value_text = ""

            if value_text:
                parts.append(f"{key_text}: {value_text}")
        return "; ".join(parts)

    @classmethod
    def _format_list(cls, value: object) -> str:
        if not isinstance(value, list):
            return ""

        parts: list[str] = []
        for item in value:
            if isinstance(item, str):
                text = item.strip()
            elif isinstance(item, dict):
                text = cls._format_mapping(item)
            else:
                text = ""
            if text:
                parts.append(text)
        return "; ".join(parts)

    @staticmethod
    def _as_text(value: object) -> str:
        return value.strip() if isinstance(value, str) else ""

    # ── Block generators ────────────────────────────────────

    @staticmethod
    def _get_layout(figure_type: str) -> str:
        layouts: dict[str, str] = {
            "flowchart": (
                "## Block 2: LAYOUT\n"
                "type: Clinical Guideline Flowchart\n"
                "structure: Top-to-bottom decision flow with branching paths\n"
                "sections: Background → Screening → Pre-op → Intra-op → Post-op → Complications\n"
                "color-coded recommendation tiers: Strong, Weak, Evidence-based"
            ),
            "mechanism": (
                "## Block 2: LAYOUT\n"
                "type: Drug Mechanism Diagram\n"
                "structure: Left-to-right pathway flow\n"
                "sections: Drug molecule → Receptor binding → Signal cascade → Clinical effect\n"
                "include: molecular structures, arrows, concentration gradients"
            ),
            "comparison": (
                "## Block 2: LAYOUT\n"
                "type: Trial Comparison\n"
                "structure: Side-by-side or forest plot layout\n"
                "sections: Treatment A vs Treatment B, outcomes table, effect sizes\n"
                "highlight: statistically significant findings"
            ),
            "infographic": (
                "## Block 2: LAYOUT\n"
                "type: Medical Infographic\n"
                "structure: Multi-section with clear headers and visual hierarchy\n"
                "sections: Key findings, statistics, clinical implications\n"
                "visuals: icons, data callouts, numbered points"
            ),
            "timeline": (
                "## Block 2: LAYOUT\n"
                "type: Timeline Evolution\n"
                "structure: Horizontal or diagonal timeline with milestones\n"
                "sections: Historical progression with key events and paradigm shifts\n"
                "mark: dates, landmark studies, guideline updates"
            ),
            "anatomical": (
                "## Block 2: LAYOUT\n"
                "type: Anatomical Reference\n"
                "structure: Cross-section or regional anatomy with labeled structures\n"
                "sections: Layered view showing depth relationships\n"
                "include: nerve pathways, vessels, fascial planes"
            ),
            "data_visualization": (
                "## Block 2: LAYOUT\n"
                "type: Data Chart / Graph\n"
                "structure: Journal-standard statistical plot\n"
                "sections: Axis labels, data points, confidence intervals, legend\n"
                "style: Nature/Lancet compliant"
            ),
        }
        return layouts.get(figure_type, layouts["infographic"])

    @staticmethod
    def _get_color_scheme(figure_type: str) -> str:
        schemes: dict[str, str] = {
            "flowchart": (
                "## Block 4: COLOR\n"
                "background: Cream (#FAF8F0) for warm educational feel\n"
                "recommendations: Green (#4CAF50) strong, Orange (#FF9800) weak, "
                "Red (#E53935) critical\n"
                "headers: Deep navy (#1A237E)\n"
                "accents: Teal (#009688) for connections\n"
                "font: Dark (#212121) for legibility"
            ),
            "mechanism": (
                "## Block 4: COLOR\n"
                "background: Clean white (#FFFFFF)\n"
                "molecules: Purple (#7B1FA2) for drugs, Blue (#1565C0) for receptors\n"
                "pathways: Green (#2E7D32) activation, Red (#C62828) inhibition\n"
                "tissue: Warm peach (#FFCC80) for anatomy context\n"
                "arrows: Bold directional color coding"
            ),
            "infographic": (
                "## Block 4: COLOR\n"
                "background: Cream (#FAF8F0) or Clean white (#FFFFFF)\n"
                "primary: Warm orange (#E65100) for headers\n"
                "secondary: Teal (#00838F) for data points\n"
                "accent: Coral (#FF6F61) for highlights\n"
                "data: ColorBrewer-safe categorical palette"
            ),
        }
        return schemes.get(
            figure_type,
            "## Block 4: COLOR\nbackground: clean white, warm accent colors",
        )

    @staticmethod
    def _get_style(figure_type: str) -> str:
        styles: dict[str, str] = {
            "flowchart": (
                "## Block 6: STYLE\n"
                "style: Professional medical flowchart, clean sans-serif labels\n"
                "icons: Minimal flat icons (pills, monitors, syringes)\n"
                "borders: Rounded corners, subtle shadows\n"
                "typography: Arial/sans-serif, clear hierarchy (title 24pt, body 14pt)\n"
                "footer: PMID, citation, 'Academic Figures Weekly'"
            ),
            "mechanism": (
                "## Block 6: STYLE\n"
                "style: Scientific illustration, clean line art with soft fills\n"
                "accuracy: Anatomically correct proportions and spatial relationships\n"
                "labels: Thin lines pointing to structures, sans-serif labels\n"
                "molecules: Simplified 2D/3D hybrid structures\n"
                "footer: PMID, citation"
            ),
        }
        return styles.get(
            figure_type,
            (
                "## Block 6: STYLE\n"
                "style: Clean flat medical illustration, Nature journal quality\n"
                "text: Must be crisp and legible (Traditional Chinese if specified)\n"
                "footer: PMID, citation, 'Academic Figures Weekly'"
            ),
        )
