# AI Model Benchmark for Medical Illustration

## Nano Banana 2 vs GPT Image 1.5 vs DALL-E — 2026 綜合比較

> 研究日期：2026-04-10
> 來源：Google Blog, WisGate Leaderboard, flowith.io, jueapi.com, intuitionlabs.ai, GitHub

---

## Nano Banana 2 (Google Gemini 3.1 Flash Image Preview)

**發布日期：** 2026-02-26
**模型 ID：** `gemini-3.1-flash-image-preview`

### 核心規格
| 項目 | 數值 |
|---|---|
| **架構** | Gemini 3.1 Flash Image |
| **Context Window** | 256K tokens |
| **輸出解析度** | 512px → 4K（完全控制 aspect ratio）|
| **生成速度** | 一致 ~20秒（0.5K-4K）|
| **API 價格** | ~$0.058/張 |
| **Subject Consistency** | 最多 5 個角色、14 個物件跨 workflow |
| **多語言文字** | ✅ 改進的跨語言 text rendering + translation |
| **Image Search Grounding** | ✅ 獨有功能（`"tools": [{"google_search": {}}]`）|
| **SynthID 浮水印** | ✅ C2PA Content Credentials（像素級嵌入）|
| **Bidirectional Output** | TEXT + IMAGE 同次回應 |

### 相比 Nano Banana 1 的改進
- **Subject consistency**：從單角色 → 5 角色 + 14 物件
- **Instruction following**：大幅增強複雜請求的精確度
- **Visual fidelity**：更豐富的光影、紋理、細節
- **World knowledge**：整合 Gemini 即時知識庫 + Google Search

---

## GPT Image 1.5 (OpenAI)

### 核心規格
| 項目 | 數值 |
|---|---|
| **WisGate Image Edit Score** | **2,726（#1 排名）**|
| **WisGate Image Gen Rank** | 頂部排名 |
| **Text Rendering** | 優於 Nano Banana 2（特別在 8-15+ 詞、styled typography、non-Latin scripts）|
| **Conversational Workflow** | ✅ ChatGPT 原生對話整合，迭代創意工作流最佳 |
| **Content Provenance** | ✅ Metadata-based |
| **Subject Consistency** | Fair（需靠 prompting，沒有原生支援）|
| **Image Search Grounding** | ❌ 不支援 |

---

## Head-to-Head 比較矩陣

### 醫學插圖相關維度

| 維度 | Nano Banana 2 | GPT Image 1.5 | 勝出 |
|---|---|---|---|
| **Photorealism（照片真實感）** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | Nano Banana 2 |
| **Skin/Material Rendering** | Excellent | Very Good | Nano Banana 2 |
| **Subject Consistency（角色一致性）** | Very Good（native）| Fair（prompting）| Nano Banana 2 |
| **Text Rendering（短標 1-8字）** | Good-Very Good | Very Good-Excellent | GPT 1.5 |
| **Text Rendering（長文 8-15+字）** | Fair | Very Good | GPT 1.5 |
| **Non-Latin Scripts** | Fair | Good | GPT 1.5 |
| **Multi-Image Fusion** | Very Good（原生支援）| Limited | Nano Banana 2 |
| **Image Editing Precision** | Score: 1,825 (#17) | Score: 2,726 (#1) | GPT 1.5 |
| **Generation Speed** | Consistent 20s | 5-20s（可變）| Nano Banana 2 |
| **Cost** | $0.058/img | 較高 | Nano Banana 2 |
| **Context Window** | 256K | 無數據 | Nano Banana 2 |
| **Search Grounding** | ✅ 即時知識 | ❌ | Nano Banana 2 |
| **SynthID Robustness** | 像素級嵌入（抗元數據清除）| Metadata-based | Nano Banana 2 |

### 醫學插圖應用場景決策

| 場景 | 模型選擇 | 理由 |
|---|---|---|
| 解剖結構教學圖（多張系列）| Nano Banana 2 | subject consistency 保持角色一致 |
| 帶有大量文字的圖表/標籤 | GPT Image 1.5 | 更準確的長文字渲染 |
| 需要「即時真實世界參考」 | Nano Banana 2 | Image Search Grounding 獨有功能 |
| 需要從一張醫學圖片上編輯/註解 | GPT 1.5 | 精確的 spatial editing + inpainting |
| 快速批次生成大量示意圖 | Nano Banana 2 | 速度快、成本低、一致性高 |
| 複雜概念需要分析後再生成 | Pro → Flash 串聯 | Pro 做文獻理解，Flash 負責生成 |

---

## Awesome Nano Banana for Medical Imaging 社群資源

**Repo:** [github.com/LijunRio/Awesome-Nano-Banana-for-Medical-Imaging](https://github.com/LijunRio/Awesome-Nano-Banana-for-Medical-Imaging)

這個 repo 展示了 Gemini-2.5-Flash-Image（Nano Banana）在醫學影像上的應用，包含 26+ 個例子：
- MRI/CT 異常區域偵測與定位
- 不健康區域移除 → 生成健康版本
- 不改變像素的註解overlay
- 移除註解/箭頭/標籤（reconstruct underlying anatomy）
- 影像視角識別（axial/sagittal/coronal）
- MRI → Ultrasound 跨模態生成
- 3D mesh 生成（brain, teeth, spine）
-腫瘤進展模擬
- 組織分割（cardiac chambers, brain glioma）

**提示意義：** Nano Banana 的醫學影像編輯能力已延伸到放射學 level，不只是插圖。

---

## 醫學插圖 Model 選擇最終建議

### 目前我們的技術棧（Gemini image generation only）

因為 Eric 規定所有繪圖任務只用 Gemini image generation API，所以：

**主力模型：** Nano Banana 2（`gemini-3.1-flash-image-preview`）
- 速度快、成本低、subject consistency 好
- 適合批量生成醫學教學插圖、示意圖系列

**需要高品質精修時：** Pro → `gemini-3-pro-image-preview`
- 多輪編輯（Thought Signatures 支援）
- 複雜概念分析

**Text-Heavy 圖表的 workaround：**
如果標籤文字太多、且 Nano Banana 2 渲染不理想：
1. 先用 Nano Banana 2 生成無文字的解剖圖
2. 用 post-production（draw.io / Figma / 甚至 Gemini text-only API）加上標籤
3. 或者 prompt 中極度精確地拼出每個文字字串

### Prompt 優化（Nano Banana 2 專用）

Nano Banana 2 相比 v1 的改進讓 prompt 可以更複雜：
- 可以用更長的 layout 描述（256K context）
- 可以利用其 subject consistency 做多圖系列
- 利用 Image Search Grounding（`tools: [{google_search: {}}]`）生成基於即時知識的圖
- 輸出同時包含 TEXT + IMAGE，可以順便要它生成 caption/metadata

---

## 參考來源

1. [Google Blog: Nano Banana 2 Announcement (2026-02-26)](https://blog.google/innovation-and-ai/technology/ai/nano-banana-2/)
2. [flowith.io: Nano Banana 2 vs GPT Image — Text Rendering Comparison](https://flowith.io/blog/nano-banana-2-vs-gpt-image-text-rendering-2026/)
3. [jueapi.com: Nano Banana 2 vs GPT Image 1.5 — Edit Accuracy vs Speed and Cost](https://www.juheapi.com/blog/nano-banana-2-vs-gpt-image-1-5-edit-accuracy-speed-cost-comparison)
4. [intuitionlabs.ai: Gemini Nano Banana Pro — Technical Review for Life Sciences](https://intuitionlabs.ai/articles/gemini-nano-banana-pro-life-sciences)
5. [Awesome Nano Banana for Medical Imaging (GitHub)](https://github.com/LijunRio/Awesome-Nano-Banana-for-Medical-Imaging)
6. [WisGate Image Leaderboard](https://wisgate.ai/studio/image)
