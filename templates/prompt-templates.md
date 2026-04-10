# Prompt Templates for Medical Figures

## Template 1: Clinical Guideline Flowchart

```
A professional medical infographic flowchart titled "[TITLE]" in Traditional Chinese.

Layout: Top-to-bottom flow with [N] main sections connected by arrows.

SECTION 1 - "[Section Name]":
- [Box description with exact text content]

SECTION 2 - "[Section Name]":
[N] colored recommendation boxes:
- [COLOR] "[Label]": "[Exact text]" with note "[Sub-text]"

[Additional sections...]

Bottom: "[Citation]"

Style: Clean medical poster, white background, professional color scheme 
(navy blue headers, colored category boxes), clear hierarchy, modern 
sans-serif typography, suitable for medical conference presentation.
```

## Template 2: Drug Mechanism Diagram

```
A medical mechanism diagram showing [DRUG/PATHWAY].

Center: [Main target/receptor]
Left side: [Input/stimulus]
Right side: [Output/effect]

Pathway arrows:
1. [Step 1] → [Step 2] → [Step 3]
2. [Branch point] → [Alternative path]

Labels: [List all labels with exact text]
Color coding: [Agonist=green, Antagonist=red, etc.]

Style: Clean pharmacology textbook illustration, white background,
labeled arrows, compartment boxes for different body systems.
```

## Template 3: Comparison Table / Trial Results

```
A professional comparison infographic for clinical trials.

Title: "[Study comparison title]"

Table layout with [N] rows:
| Trial | n | Comparison | Result |
[Exact data for each row]

Key finding highlighted: "[Main conclusion]"

Style: Clean data visualization, alternating row colors, 
bold significant results, medical journal figure quality.
```

## Template 4: Anatomy / Procedure

```
A clean medical illustration of [ANATOMY/PROCEDURE].

View: [Anterior/Lateral/Cross-section]
Key structures labeled:
1. [Structure] - [color/position]
2. [Structure] - [color/position]

Annotations: [Surgical approach arrows, measurement lines, etc.]

Style: Clean line art, medical textbook quality, labeled structures,
orientation markers (Superior/Inferior, Left/Right), white background.
```

## Prompt Modifiers (append as needed)

- "with Traditional Chinese labels" — for Chinese text
- "suitable for 16:9 presentation slide" — for slides
- "publication-ready, 300 DPI equivalent" — for papers
- "colorblind-accessible palette" — for accessibility
- "minimalist flat vector style" — for modern look
- "detailed anatomical accuracy" — for anatomy

---

## Template 5: Software / Tech Architecture Diagram (for GitHub README)

```
A publication-quality architecture diagram for "[PROJECT NAME]" — [one-line description].

Title: "[Project Name] — [Type] Architecture"
Subtitle: "[Key value proposition]"

Layout: [N]-layer / left-to-right flow / [describe structure]

LAYER 1 - "[Layer Name]" ([color]):
[Description of this layer's components, with exact labels]

LAYER 2 - "[Layer Name]" ([color]):
[Sub-boxes in a row: "Component A (N tools)" | "Component B" | "Component C"]

LAYER 3 - "[Layer Name]" ([color]):
[Connected boxes with arrows showing data flow]

[Additional layers...]

Key callout box (right side):
"[Core insight / value proposition quote]"

Footer: "[Tech stack / compatibility note]"

Style: Modern tech documentation diagram, white background, rounded corners,
professional color palette (navy, teal, coral accents), clean sans-serif
typography, suitable for GitHub README. All text in English.
```

## Template 6: Character Portrait / Profile Picture

```
Anime-style character portrait for Telegram/social media profile picture.
Character: [Name], [role/profession], [age range].

Character design:
- Physical: [hair, eyes, build]
- Expression: [describe the emotional vibe]
- Outfit: [describe clothing details]
- Props/accessories: [specific items that define the character]
- Special elements: [fantasy/conceptual elements around character]

Background:
- [Scene description — environment, time of day, lighting]

Vibe/atmosphere:
- [One sentence capturing the essence: "late-night coder who looks up at stars"]

Art style:
- [Anime style specifics — mature vs cute, realistic proportions, etc.]
- Square format, profile picture quality
- [Color palette]

No text in image.
```

---

## Med-Banana-50K Inspired: Iterative Refinement Protocol (2026-03-30)

Based on the Med-Banana-50K pipeline (arXiv:2511.00801), this protocol adapts the LLM-as-Judge approach for illustration generation:

### 4-Dimension Refinement Rubric (Post-Generation Review)
When reviewing a generated figure before sending, evaluate:

| Dimension | Pass Criterion | Fail Action |
|---|---|---|
| **Instruction Compliance** | All requested structures/labels present | Re-add missing items explicitly in retry |
| **Structural Plausibility** | No impossible anatomy (e.g., vessels not touching wrong structures) | Add "anatomically accurate spatial separation" |
| **Visual Realism** | Matches requested style (textbook/schematic/realistic) | Specify style more explicitly |
| **Fidelity** | Background/context matches intent (white bg, clean lines) | Add "white background, no artifacts, no decorative noise" |

### When to Use This vs 8-Domain Rubric
- **8-domain rubric** (ai-medical-illustration-evaluation.md): First pass, coarse score (total ≥28/40)
- **4-dimension rubric** (this): Refinement pass — diagnose *why* something failed and what to fix

### Complex Anatomy Fallback Prompt Snippet
For structures known to fail (brachial plexus, ACA branches, skull foramina):
```
"[Structure] shown as a simplified schematic diagram. 
Do NOT attempt photorealistic rendering. 
Use labeled boxes/arrows to indicate spatial relationships.
Each component clearly separated with minimum 30px visual gap."
```

---

When the first generation doesn't pass quality checklist:

1. **Identify the specific failure** (text garbled? structure wrong? style off?)
2. **Keep what worked** — don't rewrite the whole prompt
3. **Add explicit correction** — e.g., "KEY CHANGE: The badge text must clearly show..."
4. **Maximum 2 retries** — if still failing, switch to code-based rendering

---

## Template 7: Nature-Style Multi-Panel Figure (Proven Pattern — 2026-03-26)

Key insight from session: this pattern reliably produces Nature/PLOS quality output.

```
A Nature journal publication-quality multi-panel figure. Title centered top: "[TITLE]" bold, large. White background #FFFFFF, print-ready. [N] panels a/b/c/d. All text in [language].

PANEL a — top-left quadrant, bold label "a" top-left corner:
Sub-title: "[Panel title]"
[Describe layout explicitly — boxes, arrows, labels with EXACT text]

PANEL b — top-right quadrant, bold label "b" top-left corner:
Sub-title: "[Panel title]"
[Describe layout explicitly]

PANEL c — bottom-left quadrant, bold label "c" top-left corner:
Sub-title: "[Panel title]"
Clean comparison table [N] columns [N] rows:
Header row (navy background, white bold text): "Col 1" | "Col 2" | "Col 3"
Row 1: "[label]" | "[value]" | "[value]"
[... all rows explicitly listed ...]
Table style: thin borders, alternating light gray rows (#F5F5F5), header navy #1B2A4A

PANEL d — bottom-right quadrant, bold label "d" top-left corner:
Sub-title: "[Panel title]"
[Decision tree or summary]

STYLE: Nature journal figure, teal #2196A6 and coral #E8612C on white, panel labels bold black, clean sans-serif, generous white space, all text large and legible, no decorative gradients. 1536x1024 landscape.
```

### Proven techniques for this template:
- **Robot icons** render reliably for "agent" concepts
- **Dashed borders** for gateway/boundary boxes work well
- **Callout box** with coral border for key insights
- **Decision diamond** works in panel d for decision trees
- **Comparison table** with navy header is the most reliable table style
- CJK: write all Chinese characters explicitly, never use placeholders

---

## Template 8: Netter / AAAMI 醫學解剖配色標準（2026-04-08 研究整合）

> **為什麼需要這個：** Gemini 常常把不同結構畫成類似的紅色，或者把筋膜畫成實心白色不透光。加入標準配色描述可大幅減少這類錯誤。

### 配色邏輯（理論基礎）
人體結構以紅/米色為主，缺乏天然對比。顏色是**辨識工具**不是寫實還原——結構越缺乏形狀特徵，顏色越需要強烈。

### 標準顏色映射（Netter / Gray's / AAAMI 一致）

```
Arteries      → saturated glossy red #FF2200 with highlight (含氧血+高光澤，與靜脈區分)
Veins         → blue-purple #4040A0 (去氧血較暗)
Nerves        → yellow #E8C830 (細長結構需要顯眼顏色)
Muscles       → dark crimson #8B0000–#C00000 with fiber texture
              → 加 "NOT bright red (avoid conflict with artery red)"
Bone          → ivory/cream white (#FFFFF0–#FFF8DC)
Lymphatics    → green #2E8B57
Fat           → yellow-orange #FFD700–#FFA500 (顆粒狀質地)
Fascia        → translucent white-silver (30-50% opacity), thin fibrous sheet
```

### 3 個必備 Prompt 技巧

**技巧 A — 配色衝突迴避（肌肉不是动脉红）**
```
deep crimson red #8B0000 with fiber texture, NOT bright red (avoid conflict with artery red)
```

**技巧 B — 功能性理由強化（告诉 Gemini 為什麼要這個顏色）**
```
Arteries are saturated glossy red because they carry oxygenated blood and must be immediately 
distinguishable from veins; veins are blue-purple #4040A0
```

**技巧 C — 筋膜透明度明確指定**
```
Fascia as thin translucent white-silver sheet (30-50% opacity) wrapping around structures, 
fibrous weave texture visible
```
→ 不寫 opacity 容易畫成不透明白色

### 複雜解剖 Fallback Snippet

ACA branches、臂叢神經、顱底孔裂、冠狀動脈起源等結構即使 advanced prompting 也容易失敗：
```
[Structure] shown as a simplified schematic diagram. 
Do NOT attempt photorealistic rendering. 
Use labeled boxes/arrows to indicate spatial relationships.
Each component clearly separated with minimum 30px visual gap.
```

### 兩層評估流程

1. **粗評** → Davis 8域量表（各1-5分，閾值：任一域<3或總分<28/40 → 重試）
2. **精煉** → Med-Banana 4維度（Instruction Compliance / Structural Plausibility / Image Realism / Fidelity）

詳見：`references/ai-medical-illustration-evaluation.md`

---

## Template 9: Nature/Lancet Journal-Ready Figure（2026-04-09 新增）

> **適用於：需要符合期刊投稿標準的圖表。**
> 完整規格見 `references/journal-figure-standards.md`

### Nature-style

```
A Nature journal publication-quality figure. White background #FFFFFF.
Figure width: single column (89mm equivalent), Arial font 5-7pt.
Panel labels: bold lowercase a, b, c in upper-left corner (8pt bold).
Color scheme: Wong colorblind-safe palette — orange #E69F00, sky blue #56B4E9, bluish green #009E73, yellow #F0E442, blue #0072B2, vermillion #D55E00.
No background gridlines, no drop shadows, no decorative icons, no patterns.
All text labels in black, sans-serif font. RGB colour space.
Clean minimal layout, publication-ready, 300 DPI minimum.

[Content description: what the figure should show]
```

### Lancet-style

```
A The Lancet journal publication-quality figure. White background.
Figure width: single column (79mm equivalent), Arial font 8-10pt.
Panel labels: bold uppercase A, B, C.
Clean clinical layout, no vertical lines in tables, horizontal lines only at top/header/bottom.
Publication-ready, 300 DPI minimum.

[Content description: what the figure should show]
```

