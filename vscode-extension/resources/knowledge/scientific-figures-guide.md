# AI Scientific Figures — Best Practice Guide

Source: [awesome-ai-scientific-figures](https://github.com/YupengQI99/awesome-ai-scientific-figures) (深讀 2026-03-27)

## Core Philosophy

> **"It doesn't matter which AI you use. What matters is the output format AI generates and the tool that renders it."**

**AI + output format + rendering tool = best result**

AI doesn't draw directly. It generates intermediate code → Tool renders final figure.
Choosing the right combination is the key skill.

---

## Decision Matrix: Which Combination?

```
What figure do you need?
│
├─ Statistical data plots (real data to visualize)
│   └─ → AI + Python (matplotlib/seaborn) ⭐ Best quality
│
├─ Flowcharts (methodology, experiment pipeline)
│   ├─ Quick draft → AI + Mermaid
│   └─ Polished → AI + Mermaid → import into draw.io
│
├─ Architecture / Neural Network / Concept diagrams
│   ├─ Quick output → AI + SVG
│   └─ LaTeX papers → AI + TikZ
│
├─ Math / Geometry figures
│   └─ → AI + TikZ
│
└─ Software system design (UML)
    └─ → AI + PlantUML
```

## Comparison Table

| Route | AI Output | Renderer | Best For | Difficulty | Quality |
|-------|-----------|----------|----------|------------|---------|
| 01-Python | Python code | matplotlib/seaborn/plotly | Statistical plots | Medium | ⭐⭐⭐⭐⭐ |
| 02-SVG | SVG code | Browser/Inkscape | Architecture, neural nets, concept | Low | ⭐⭐⭐⭐ |
| 03-Mermaid | Mermaid code | Mermaid Live/draw.io | Flowcharts, sequence diagrams | Low | ⭐⭐⭐ |
| 04-TikZ | TikZ code | LaTeX | Math figures, paper-embedded | High | ⭐⭐⭐⭐⭐ |
| 05-PlantUML | PlantUML | PlantUML renderer | UML class diagrams | Medium | ⭐⭐⭐ |

---

## 01 — AI + Python (Statistical Plots)

**Evidence:** MatPlotAgent (ACL 2024) — GPT-4 direct: 48.86/100 → with iterative agent: 72.62 → with visual feedback: 75.14. Always iterate.

### Key Best Practices

1. **Separate data from styling** — Ask AI to put all configurable parameters at the top as variables:
   ```python
   # === CONFIGURABLE PARAMETERS ===
   COLORS = ['#2196F3', '#FF5722', '#4CAF50']
   FONT_SIZE = 12
   FONT_FAMILY = 'Times New Roman'
   FIG_WIDTH, FIG_HEIGHT = 10, 6
   DPI = 300
   # === END PARAMETERS ===
   ```

2. **Use SciencePlots for instant journal-ready styling:**
   ```python
   import scienceplots
   plt.style.use(['science', 'ieee'])  # or 'nature', 'grid'
   ```

3. **Generate complex figures panel-by-panel**, not all at once. Verify each panel then combine.

4. **Always verify numerical accuracy** — bar heights, axis scales, legend labels.

### Medical Research Prompt Template (Statistical)

```
Generate Python code using matplotlib to create a [CHART TYPE] for a medical research paper:

Data:
- [describe your data or paste CSV]

Requirements:
- Figure size: (10, 6), DPI: 300
- Font: Times New Roman, size 12 (matches most journal requirements)
- X-axis: [label with units]
- Y-axis: [label with units]
- Color palette: ['#2196F3', '#FF5722', '#4CAF50', '#FF9800']
- Include error bars (mean ± SEM or 95% CI as appropriate)
- Include p-value annotations where appropriate (use ns / * / ** / ***)
- Legend in upper right
- Save as both PDF (vector) and PNG (300 DPI)

Style:
- Remove top and right spines (Tufte style)
- Grid: light gray (#E0E0E0), dashed, alpha=0.3
- SciencePlots 'science' style if available, else manual

Put ALL configurable parameters at the top as variables.
```

### Known Limitations
- Numerical hallucination — bar heights may not match scale. Always verify data accuracy.
- Label overlap — use `plt.tight_layout()` or manual `bbox_to_anchor`.
- Style inconsistency — specify color palette explicitly in every prompt.
- Complex multi-panel layouts often break — generate panels separately.

---

## 02 — AI + SVG (Architecture & Concept Diagrams)

**Best for:** Architecture diagrams, neural network structure, concept illustrations, roadmaps.

**Evidence:** Widely validated — users report 1 min generation vs 15+ min manual drawing.

### Key Best Practices

1. **Always include anti-overlap instructions in every SVG prompt:**
   - "No overlapping elements"
   - "Minimum 20px gap between elements"
   - "Text must not extend beyond container boundaries"

2. **Specify canvas size explicitly:**
   ```
   Canvas size: 1200x600
   ```

3. **Keep it simple — 5-10 nodes max.** Beyond that, switch to Mermaid or draw.io.

4. **Post-edit in Inkscape (free) or Illustrator** for publication quality.

5. **Iterate — generate 3-5 versions**, pick best, then refine manually.

### Medical SVG Prompt Template (Pathway/Mechanism)

```
Create an SVG diagram showing [DRUG/MECHANISM NAME] mechanism of action.

Elements:
- [List receptors, enzymes, cellular components]
- [Describe signal pathway steps]
- [List downstream effects]

Connections:
- [Describe arrows: activation (→), inhibition (⊣), catalysis (⟹)]

Style:
- Rounded rectangles for proteins/receptors, 8px border radius
- Diamond shapes for key decision points
- Colors:
  - Receptor: #4FC3F7 (light blue)
  - Inhibition: #EF9A9A (light red)
  - Activation: #A5D6A7 (light green)
  - Drug: #FFE082 (amber)
- Canvas: 1200x800
- Font: Arial, 12px for labels, 10px for subtext
- CRITICAL: No overlapping elements, min 20px gap between all elements
- White background
```

---

## 03 — AI + Mermaid (Flowcharts & Pipelines)

**Best for:** Methodology flowcharts, experiment pipelines, sequence diagrams.

**Recommended workflow:**
```
AI → Mermaid code → Import into draw.io → Fine-tune → Export PDF/PNG
```

### Key Best Practices

1. **Medical color convention for Mermaid:**
   ```mermaid
   style A fill:#E3F2FD,stroke:#1565C0    %% Input: light blue
   style C fill:#FFEBEE,stroke:#C62828    %% High-risk: light red
   style D fill:#E8F5E9,stroke:#2E7D32    %% Low-risk: light green
   style E fill:#FFF8E1,stroke:#F9A825    %% Decision: amber
   ```

2. **Avoid special characters in node labels** (parentheses, quotes, brackets cause errors).

3. **Max ~12 nodes** before auto-layout gets confusing.

4. **Use `graph TD` for vertical, `graph LR` for horizontal pipelines.**

### Medical Methodology Flowchart Template

```
Generate a Mermaid flowchart for the following research methodology:

Steps:
1. [Step name] - [brief description]
2. [Step name] - [brief description]
...

Decision points:
- After step X: if [condition] → [next step], else → [other step]

Requirements:
- Use `graph TD` for patient flow, `graph LR` for data pipeline
- Rectangles for process steps, diamonds for decisions
- Stadium-shaped nodes (([...]]) for start/end
- Concise labels (max 5 words per node)
- NO special characters in labels (no parentheses, quotes, brackets)
- Add style blocks using the medical color convention above
- Use class definitions for consistent styling across multiple nodes
```

---

## Route Selection for Medical Research

| Medical Figure Type | Recommended Route | Notes |
|---------------------|-------------------|-------|
| Forest plot | Python + matplotlib | Precise CIs required |
| Kaplan-Meier curve | Python + matplotlib | Statistical precision |
| ROC curve | Python + matplotlib | AUC annotation |
| Drug mechanism pathway | SVG or direct image | Complex visuals |
| Clinical protocol flowchart | Mermaid → draw.io | Easy to edit |
| Neural network architecture | SVG or TikZ | Depends on detail |
| Anatomical diagram | Direct image (Gemini) | Code can't draw anatomy |
| Drug comparison table figure | Python (matplotlib table) | Precise text control |

---

## SciencePlots Reference

Journal styles available:
- `['science']` — generic Science format
- `['science', 'ieee']` — IEEE transactions
- `['science', 'nature']` — Nature journals
- `['science', 'no-latex']` — No LaTeX rendering (faster)
- `['science', 'grid']` — With gridlines

Installation: `pip install SciencePlots`
GitHub: https://github.com/garrettj403/SciencePlots

---

## PaperBanana 框架：5-Agent 雙模式輸出策略

Source: [PaperBanana (JackaZhai/SCIdrawer integration)](https://github.com/JackaZhai/SCIdrawer/tree/main/integrations/PaperBanana) + [arXiv:2601.23265](https://arxiv.org/abs/2601.23265) (研究日期 2026-03-28)

### 核心洞見：雙模式輸出

PaperBanana 最重要的貢獻是明確區分兩種圖表類型，採用完全不同的生成策略：

| 圖表類型 | 生成策略 | 核心優勢 | 代表類型 |
|---|---|---|---|
| **方法論配圖** | Image Gen（Gemini/Nano Banana Pro） | 快速、美觀、複雜結構精準 | 架構圖、流程圖、管線圖、模型示意圖 |
| **統計圖表** | Matplotlib 代碼生成 | **零數值幻覺**，100%精確 | Bar chart、Line chart、Scatter plot、Forest plot |

→ **消滅數值幻覺 = 統計類用代碼，視覺類用生成**。這個策略直接解決了我們在生成精確數值圖表時的最大痛點。

### 5-Agent Pipeline 架構

```
PaperBanana 兩階段流程：

Phase 1（線性規劃）:
  Retriever → Planner → Stylist
  (相似圖檢索) (內容規劃) (學術風格統一)

Phase 2（迭代優化）:
  Visualizer ↔ Critic × 3 rounds
  (圖像生成)   (品質審查)
```

**Critic Agent 4 維度評估（每輪迭代後）：**
- Fidelity（內容忠實度）：+2.8%
- Conciseness（簡潔度）：**+37.2%** ⭐ 進步最大
- Readability（可讀性）：+12.9%
- Aesthetics（美觀度）：+6.6%

**5 個 Agent 職責：**
| Agent | 輸入 | 輸出 |
|---|---|---|
| Retriever | 方法論文字 | 相似 reference 圖 |
| Planner | 文字 + 參考圖 | 結構化 layout plan |
| Stylist | 參考圖集合 | 學術風格指南（配色/字體/圖標） |
| Visualizer | plan + style guide | 生成圖像（Nano Banana Pro） |
| Critic | 生成圖 + 原始描述 | 4維度分數 + 修改建議 |

### 可借鏡的實踐

1. **跟我們的 workflow 整合：** 我們在生成統計圖（Forest plot、KM curve）時，可以明確要求「生成 Python matplotlib 代碼」而非直接生圖
2. **Critic 審查思維：** 複雜醫學插圖可以加一個「4 維度自檢」步驟（語意正確、資訊簡潔、佈局清晰、視覺美觀）
3. **Experiment modes：** SCIdrawer 支援 vanilla / planner / planner+critic / full，可視需求選擇

### Known Limitations
- 輸出僅支援 PNG/JPG（無 SVG/PDF 向量格式）
- 複雜配圖忠實度 45.8%，未達人工基線，建議重要圖手動審核
- 局部修改需整圖重生成

---

*Last updated: 2026-03-27 from awesome-ai-scientific-figures deep read + 2026-03-28 PaperBanana research*

