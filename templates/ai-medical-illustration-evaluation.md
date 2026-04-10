# AI-Generated Medical Illustration: Quality Evaluation Standards

Sources researched: 2026-03-29

---

## Key Studies

### 1. Gemini vs Other Models — Neurosurgery Illustrations
**Paper:** Davis et al., *Clinical Neurology and Neurosurgery* 2025 Oct
**PMID:** 40614319 | DOI: 10.1016/j.clineuro.2025.109039

**What they tested:**
- 4 models: DALL-E, Copilot, **Gemini**, Midjourney
- 9 neurovascular topics (aneurysms, AVM, endovascular procedures)
- 3-stage evaluation: proof-of-concept → advanced prompting → expert validation

**Key results:**
- Gemini outperformed all others in accuracy, color, and educational value
- Advanced prompting dramatically improved scores: fusiform aneurysm 22.4 → 35.0 (max 40), p=7E-08
- **85% of neurosurgeons** said saccular aneurysm image needed no modification for manuscript use
- Complex anatomy still fails: anterior cerebral arteries scored Accuracy 2.18/5, Educational value 2.20/5

**Scoring rubric (8 domains, 1-5 scale each, max 40):**
| Domain | What it measures |
|---|---|
| Accuracy | Anatomically correct structures |
| Location | Spatial relationship between structures |
| Size/Scale | Proportional representation |
| Color | Appropriate anatomical color coding |
| Complexity | Appropriate detail level for intended use |
| Educational Value | Teaching utility |
| Relevance | How well it matches the prompt |
| Aesthetic Quality | Visual clarity and professional appearance |

### 2. Anatomical Accuracy: 4 AI Tools in Anatomy Education
**Paper:** *Clinical Anatomy* 2025 (Wiley) | DOI: 10.1002/ca.70002

**Tested:** Microsoft Bing, DeepAI, Freepik, **Gemini**
**Focus:** Anatomy education use cases
**Finding:** All tools require expert review; Gemini among better performers but all show issues with complex structures

### 3. Why Standard Metrics Fail for Medical AI Images
**Paper:** Deo et al., *arXiv:2505.07175* (York/Leeds/Manchester)

**Key finding:**
- Common no-reference metrics (FID, BRISQUE, NIQE etc.) **correlate poorly** with clinical utility
- Metrics are insensitive to **localized anatomical inaccuracies** — a score looks fine even when anatomy is wrong
- Data memorization artifacts can also score misleadingly high

**Practical implication:** Never use visual quality metrics alone. Use:
1. **Expert evaluation** (most reliable)
2. **Downstream task performance** (e.g., can a learner identify structures correctly from this image?)
3. Multi-domain rubric like the 8-domain scoring above

---

## Med-Banana-50K: LLM-as-Judge Quality Framework

**Paper:** Chen et al., *arXiv:2511.00801* (2026-02-08 全資料集發布)
**Dataset:** 50,635 成功醫學圖像編輯 + 37,822 失敗案例（帶評估日誌）
**GitHub:** https://github.com/richardChenzhihui/med-banana-50k
**HuggingFace:** RichardChenZH/Med-Banana-50K (MIT License)

**核心架構 — 4維度 Judge Rubric:**
| 維度 | 說明 |
|---|---|
| Instruction Compliance | 是否遵循文字指令（新增/移除病灶）|
| Structural Plausibility | 解剖結構合理性 |
| Image Realism | 符合模態（X光/MRI/眼底）的視覺真實感 |
| Fidelity Preservation | 保留原圖的非目標區域（雜訊/紋理/偽影）|

**迭代精煉策略（最多5輪）：**
1. Gemini-2.5-Flash-Image 生成編輯
2. Gemini-2.5-Pro 作為 Judge 評分
3. 失敗 → history-aware refinement → 重試
4. 5輪後仍失敗 → 標記為 negative example（用於 DPO 訓練）

**對繪晴的啟示：**
- "LLM-as-Judge + 迭代精煉" 模式直接適用：生圖 → 自評 → 針對失分維度修改
- 4維度 rubric 與既有 8域量表互補（8域=粗評，4維度=精煉時用）
- 37K 失敗案例的存在說明：30%+ 的生成需要重試，失敗是正常的

---

## Anatomical Illustration — Comparative Study (2025)

**Paper:** Noel, *Anatomical Sciences Education*, 2024 Jul-Aug (PMID 37694692)
**Paper 2:** Surg Radiol Anat 2025, DOI 10.1007/s00276-025-03699-5

**共同發現（多研究一致）：**
- 所有 AI 工具在**細節結構**（孔裂、縫合線、動脈分支）上均有明顯缺陷
- 視覺美觀≠解剖準確：高 aesthetic score 的圖仍可能有嚴重解剖錯誤
- 人工核查不可省略

**Noel 2024 測試的失敗清單（值得記住）：**
- 頭顱：mental/supraorbital foramina 常被遺漏，suture lines 不準確
- 心臟：冠狀動脈起源錯誤，主動脈/肺動脈幹分支不正確
- 腦：gyri/sulci 不準確，cerebellum-temporal lobe 空間關係不清

---

## Actionable Guidelines for繪晴

### Self-Evaluation Checklist (use after generating)
When self-evaluating medical illustrations, score mentally on the 8-domain rubric:

1. **Accuracy** (1-5): Are anatomical structures correct? No extra/missing structures?
2. **Location** (1-5): Spatial relationships between structures correct?
3. **Size/Scale** (1-5): Proportions look realistic?
4. **Color** (1-5): Appropriate anatomical color coding?
5. **Complexity** (1-5): Right level of detail for the task?
6. **Educational Value** (1-5): Would a medical student learn from this?
7. **Relevance** (1-5): Does it match what was requested?
8. **Aesthetics** (1-5): Clean, professional, publication-ready?

**Threshold:** If any domain < 3, retry. If total < 28/40, retry.

### Known Difficult Anatomical Structures (Gemini-specific)
These tend to fail even with advanced prompting — use simplified/schematic style:
- Anterior cerebral artery branches
- Brachial plexus (complex nerve network)
- Fine vascular anastomoses
- Multi-plane 3D anatomy (e.g., skull base foramina)

**Strategy for complex anatomy:** Use schematic/diagrammatic style instead of realistic style. Add instruction: "simplified schematic diagram, not photorealistic, clear structure separation"

### Advanced Prompting Payoff
Evidence shows advanced prompting nearly doubles quality scores. Always use the full 7-block prompt structure from SKILL.md, especially:
- Block 3 (anatomical content): name each structure explicitly
- Block 5 (style constraints): mention "advanced medical illustration style, anatomically accurate"
- Block 7 (negative): add "no overlapping structures, clear spatial separation"
