"""
7-Block Prompt Engine
Generates structured prompts for Gemini image generation.
Based on prompt-templates.md + journal-figure-standards.md + anatomy-color-standards.md
"""

import re
from pathlib import Path
from typing import Optional

# Figure type → template mapping
FIGURE_TYPE_TO_TEMPLATE = {
    "flowchart": "clinical_guideline_flowchart",
    "mechanism": "drug_mechanism",
    "comparison": "trial_comparison",
    "infographic": "general_infographic",
    "timeline": "timeline_evolution",
    "annotated_image": "annotated_photograph",
    "anatomical": "anatomical_reference",
    "data_visualization": "data_chart",
    "statistical": "data_chart",
}


class PromptEngine:
    """Loads reference files and generates 7-block prompts."""
    
    def __init__(self, template_dir: Optional[str] = None):
        if template_dir is None:
            template_dir = str(Path(__file__).parent.parent / "templates")
        self.template_dir = Path(template_dir)
        self._templates = {}
        self._color_standards = None
        self._journal_standards = None
        self._load_all()
    
    def _load_all(self):
        """Load all reference files."""
        try:
            self._load_templates()
            self._load_color_standards()
            self._load_journal_standards()
        except Exception as e:
            print(f"Warning: Failed to load some templates: {e}")
    
    def _load_templates(self):
        """Load prompt-templates.md and parse individual templates."""
        prompt_file = self.template_dir / "prompt-templates.md"
        if not prompt_file.exists():
            print(f"Warning: {prompt_file} not found")
            return
        
        content = prompt_file.read_text()
        # Parse templates - each starts with ### Template N:
        templates = re.split(r'###\s*Template\s*\d+:', content)
        for tpl in templates[1:]:  # Skip content before first template
            lines = tpl.strip().split('\n')
            name = lines[0].strip() if lines else "unknown"
            template_name = name.split('(')[0].split('-')[0].strip()
            template_name = template_name.lower().replace(' ', '_')
            self._templates[template_name] = content  # Store full content for now
    
    def _load_color_standards(self):
        """Load anatomy color standards."""
        color_file = self.template_dir / "anatomy-color-standards.md"
        if color_file.exists():
            self._color_standards = color_file.read_text()
    
    def _load_journal_standards(self):
        """Load journal figure standards."""
        journal_file = self.template_dir / "journal-figure-standards.md"
        if journal_file.exists():
            self._journal_standards = journal_file.read_text()
    
    def build_prompt(
        self,
        paper_info: dict,
        figure_type: str = "infographic",
        language: str = "zh-TW",
        output_size: str = "1024x1536",
    ) -> str:
        """
        Build a complete 7-block prompt for Gemini.
        
        Block 1: TITLE+PURPOSE
        Block 2: LAYOUT
        Block 3: ELEMENTS
        Block 4: COLOR
        Block 5: TEXT
        Block 6: STYLE
        Block 7: SIZE
        """
        title = paper_info.get("title", "Untitled")
        authors = paper_info.get("authors", "Unknown")
        journal = paper_info.get("journal", "")
        pmid = paper_info.get("pmid", "")
        abstract = paper_info.get("abstract", "")
        
        # Block 1: TITLE + PURPOSE
        block1 = f"## Block 1: TITLE & PURPOSE\ntitle: '{title}'\npurpose: Academic medical figure visualizing key findings from PMID {pmid}"
        
        # Block 2: LAYOUT (figure-type specific)
        block2 = self._get_layout(figure_type)
        
        # Block 3: ELEMENTS
        block3 = f"## Block 3: ELEMENTS\npaper_title: '{title}'\nabstract_length: {len(abstract) if abstract else 0} chars"
        
        # Block 4: COLOR
        block4 = self._get_color_scheme(figure_type)
        
        # Block 5: TEXT
        lang_text = f"Traditional Chinese ({language})" if language == "zh-TW" else language
        block5 = f"## Block 5: TEXT\nlanguage: {lang_text}\ncitation: '{authors} · {journal}'\npmid: PMID {pmid}"
        
        # Block 6: STYLE
        block6 = self._get_style(figure_type)
        
        # Block 7: SIZE
        block7 = f"## Block 7: SIZE\ncanvas: {output_size}"
        
        return "\n\n".join([block1, block2, block3, block4, block5, block6, block7])
    
    def _get_layout(self, figure_type: str) -> str:
        """Get layout guidelines for the figure type."""
        layouts = {
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
    
    def _get_color_scheme(self, figure_type: str) -> str:
        """Get color scheme recommendations."""
        schemes = {
            "flowchart": (
                "## Block 4: COLOR\n"
                "background: Cream (#FAF8F0) for warm educational feel\n"
                "recommendations: Green (#4CAF50) strong, Orange (#FF9800) weak, Red (#E53935) critical\n"
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
        return schemes.get(figure_type, schemes.get("infographic", "## Block 4: COLOR\nbackground: clean white, warm accent colors"))
    
    def _get_style(self, figure_type: str) -> str:
        """Get style guidelines."""
        styles = {
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
        return styles.get(figure_type, (
            "## Block 6: STYLE\n"
            "style: Clean flat medical illustration, Nature journal quality\n"
            "text: Must be crisp and legible (Traditional Chinese if specified)\n"
            "footer: PMID, citation, 'Academic Figures Weekly'"
        ))
