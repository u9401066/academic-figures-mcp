# Gemini Image Generation Tips

Source: Google Cloud Vertex AI docs (2026-03-16) + deep read 2026-03-27

## Official Best Practices

1. **Be specific** — More details = more control. Instead of "flowchart", describe each element
2. **Provide context and intent** — "Create a medical conference poster showing..." helps the model
3. **Iterate and refine** — Use follow-up prompts: "Make the text larger", "Change colors to navy"
4. **Step-by-step instructions** — For complex scenes, describe in stages
5. **Positive descriptions** — Say what you want, not what you don't want
6. **Camera/view control** — Use terms like "top-down diagram", "flat illustration", "isometric view"
7. **Prompt for images explicitly** — Use "create an image of" or "generate an image of"
8. **Thought Signatures** — In multi-turn editing, pass thought signatures back for context preservation

## Multi-Turn Editing — How It Works

Multi-turn editing allows iterative refinement of the same image across conversation turns.

**Requirements:**
- Use Gemini 3 Pro Image model (not Flash)
- Pass `thought_signatures` from the previous response back in the next request
- Each response includes `thought_signatures` — opaque bytes that encode the model's "intent"

**Workflow:**
```
Turn 1: "Generate an anatomy diagram of the brachial plexus"
         → Returns image + thought_signatures

Turn 2 (with thought_signatures): "Add labels to each nerve root"
         → Returns updated image + new thought_signatures

Turn 3 (with thought_signatures): "Change the color of C5-C6 to red"
         → Returns final image
```

**Why thought signatures matter:** Without them, each turn is treated as a new generation request. With them, the model maintains context about its previous decisions (composition, style, spatial arrangement), enabling coherent incremental edits.

**When to use multi-turn:**
- Iterative label refinement
- Progressive complexity building (start simple, add detail)
- Color/style corrections while preserving structure
- Adding annotations to generated anatomy diagrams

**When NOT to use multi-turn:**
- Major structural changes (start fresh instead)
- When Flash model is sufficient (Flash doesn't support thought signatures)

## Medical-Specific Tips

- Always spell out medical terms exactly (abbreviations + full form)
- Specify anatomical orientation when relevant
- Use "clean medical illustration style" or "clinical diagram style" 
- For CJK text: write the exact characters in the prompt, repeat important labels
- Add "white background, professional, suitable for medical journal" for clean output

## Iterative Refinement Strategy (MatPlotAgent principle applied to Gemini)

Based on MatPlotAgent (ACL 2024) evidence that iterative feedback improves quality from ~50% to ~75%:

1. **First generation:** Focus on structure and layout, don't perfect details
2. **Second turn:** Fix critical accuracy issues (anatomy, labels)
3. **Third turn:** Refine aesthetics (colors, spacing, font size)

This 3-turn approach is more efficient than trying to perfect a prompt in one shot.

## Model Selection

- `gemini-3.1-flash-image-preview` (Nano Banana 2): Fast, consistent ~20s, 256K context, subject consistency up to 5 characters + 14 objects, Image Search Grounding, SynthID watermark, ~$0.058/image — **our primary model (2026-04-10)**
- `gemini-3-pro-image-preview` (Nano Banana Pro): Higher quality, better text rendering, multi-turn editing with Thought Signatures, 1M context window
- GPT Image 1.5 (OpenAI): #1 on WisGate edit benchmark (2726), superior text rendering for long strings/non-Latin, but no subject consistency native, no search grounding, no Gemini API

## Nano Banana 2 專用技巧（2026-04-10 新增）

### 與 Nano Banana 1 的差異
- **Subject consistency 躍升：** 單一角色 → 最多 5 角色 + 14 物件跨 workflow
- **可解更複合的 prompt：** 256K context window 允許更長的 layout 描述
- **Image Search Grounding：** 加入 `"tools": [{"google_search": {}}]` 可讓模型查即時資訊（但我們目前主要用 Gemini API 生成，不一定需要）
- **Bidirectional TEXT + IMAGE 輸出：** 可以一次得到圖片 + caption/metadata

### 長文字標籤的 Workaround
如果圖表中的標籤文字太多（超過 8-15 個字）：
1. **策略 A：** 先用 Nano Banana 2 生成無文字的解剖/結構圖
2. **策略 B：** 用 post-production（draw.io / Figma / 甚至 Gemini text-only model）加上標籤
3. **策略 C：** prompt 中極度精確地 spell out 每個文字字串，用 7-block structure 寫清楚

### 與 GPT Image 1.5 的關鍵差異
| 優勢 | Nano Banana 2 | GPT 1.5 |
|---|---|---|
| Photorealism | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ |
| Subject consistency | Very Good (native) | Fair (needs prompting) |
| Speed | Consistent 20s | Variable 5-20s |
| Cost | $0.058/張 | 較高 |
| Search Grounding | ✅ | ❌ |
| Text rendering (長文字) | Fair | Very Good |
| Editing precision | Score 1825 (#17) | Score 2726 (#1) |

> 完整比較矩陣見 `references/model-benchmark.md`

---

## Known Limitations

- CJK text may be garbled — always verify Chinese/Japanese characters
- Complex flowcharts may lose structure — consider code-based rendering instead
- Fine anatomical detail is unreliable — use for schematic/diagrammatic only
- Multi-turn editing requires Gemini 3 Pro Image + Thought Signatures
- Thought signatures are model-version specific — don't mix across model versions
- Complex vascular anatomy (ACA branches, brachial plexus) consistently scores low (~2.2/5) even with advanced prompting — use schematic style

## Evidence-Based Quality Benchmarks (Davis et al. 2025, PMID 40614319)

Gemini benchmarked against DALL-E, Copilot, Midjourney for neurosurgical illustrations:
- Gemini #1 for accuracy, color, educational value
- Advanced prompting improves scores dramatically (22.4 → 35.0/40, simple → advanced)
- 85% expert acceptance rate for well-prompted simple anatomy (saccular aneurysm)
- Complex anatomy still fails: ~2.2/5 accuracy for detailed vascular structures

**Self-evaluation rubric** (8 domains, 1-5 each, threshold: all ≥3, total ≥28/40):
Accuracy · Location · Size/Scale · Color · Complexity · Educational Value · Relevance · Aesthetics

See: `references/ai-medical-illustration-evaluation.md` for full rubric and checklist

---

## Gemini 2.5 Flash Image vs Pro — 2025 實戰選擇決策樹

> 研究日期：2026-04-08 | 來源：LMArena benchmarks, CometAPI, toolkitbyai.com

### 兩個模型的定位

| | **Gemini 2.5 Flash Image**（Nano Banana）| **Gemini 2.5 Pro** |
|---|---|---|
| **代號** | Nano Banana | Deep Think mode 可用 |
| **核心能力** | 文生圖、局部編輯、多圖融合、character consistency | 長文本理解、多步推理、結構化輸出（JSON/code）|
| **延遲** | 低（批次 50 張圖，Flash 延遲遠低於 Pro）| 高（每次 inference 成本較高）|
| **成本** | ~$0.039/張（1290 tokens × $30/M）| 較高（per-inference 非 per-圖）|
| **Context window** | 中等（單次請求足夠）| 極大（可處理數十頁文檔）|
| **Character consistency** | ✅ 支援（同一角色跨多次編輯保持視覺特徵）| ❌ 非主要能力 |
| **Multi-turn editing** | 需要手動傳 thought_signatures（需 Pro）| ✅ 原生支援（Deep Think）|
| **Benchmark（LMArena）** | #1 Text-to-Image + #1 Image Edit（Overall 1147）| 非圖像生成模型 |

### 什麼任務選哪個

**→ 選 Flash Image：**
- 大量批次生成醫學教學插圖（漫畫系列、示意圖）
- 產品/角色/解剖結構需要跨多張圖保持一致（character consistency）
- 快速迭代實驗（不同角度、配色、构图）
- 單張插圖的局部編輯（inpainting, background swap, style restyling）
- 多圖融合（3張輸入 → 1張合成）

**→ 選 Pro：**
- 複雜文獻調研 → 視覺化規劃（Pro 解析文獻，規劃需要什麼類型的圖）
- Agentic workflows（多步驟推理、工具調用）
- 需要結構化輸出（JSON、程式碼、chart 建議）
- Deep Think 模式（數學/編碼等高度複雜推理）

### 推薦工作流：Pro + Flash 串聯

```
文獻/複雜概念
    ↓
Pro 分析架構 → 規劃視覺化類型 → 決定圖表策略
    ↓
Flash Image 高效生成（可批次）
    ↓
如需多輪精修 → Pro 做 refinement planning → Flash 執行
```

### Flash Image 醫學插圖專用技巧

- **Series consistency**：第一張 prompt 加入「same patient/same specimen, consistent illustration style across series」，後續圖使用相同風格描述
- **批次生成**：一次 request 多張不同變體（不同角度/配色），減少來回迭代
- **Medical-specific 修飾詞**：「clean white background, medical journal quality, anatomical accuracy, professional illustration style」

### 已知限制

- Flash Image **不支援 Thought Signatures**（需要 Pro）；精細多輪編輯場景還是需要 Pro
- 複雜解剖結構（brachial plexus、ACA branches）無論哪個模型都需要 schematic style fallback
- LMArena benchmark 主觀偏好評分，與醫學準確度無直接相關

---
