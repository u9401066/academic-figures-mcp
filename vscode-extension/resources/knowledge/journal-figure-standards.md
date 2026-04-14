# Journal Figure Standards — Nature & Lancet

> 來源：Nature official figure guide (research-figure-guide.nature.com) + Lancet formatting guide
> 研究日期：2026-04-09

---

## Nature Portfolio

來源：https://research-figure-guide.nature.com/

### 尺寸規格

| 類型 | 寬度 | 適用 |
|---|---|---|
| Single column | **89 mm (3.5")** | 單一圖表、bar chart |
| 1.5 column | 120–136 mm (4.7–5.4") | 兩面板圖、寬圖例 |
| Double column | **183 mm (7.2")** | 整頁寬多面板圖 |
| 最大高度 | **247 mm (9.7")** | 含圖例空間 |

### 字體規範

- **字族：** Sans-serif only — Arial 或 Helvetica
- **面板標籤：** 8 pt **粗體**、小寫 a, b, c（左上角）
- **其他文字：** 5–7 pt（最小 5pt，最大 7pt）
- **胺基酸序列：** Courier（等寬），單字母代碼，50 或 100 字一行
- **禁止：** 文字轉輪廓（outline text）、彩色列
- **Python 設定：** `matplotlib.rcParams['pdf.fonttype'] = 42`
- **嵌入字體：** TrueType 2 或 42（不要選 TrueType 3）

### DPI 要求

| 類型 | 最低 DPI |
|---|---|
| 線條圖（graphs, charts） | **1000+ DPI** 或向量格式 |
| 照片 / 顯微鏡影像 | 300–600 DPI |
| 混合（照片 + 文字/圖表） | **600 DPI** |

### 檔案格式

| 用途 | 格式 |
|---|---|
| 主圖（Main figures）| **PDF / EPS**（向量，可編輯層） |
| 主圖（其他可接受） | .ai, layered .psd, .svg（plain SVG）, .ppt 轉 .pdf |
| Extended Data | **JPEG**（首選）, TIFF, EPS |
| 不接受 | PNG, JPEG, TIFF 用於線條圖；Canvas, DeltaGraph, Tex, ChemDraw, SigmaPlot |

### 色彩與無障礙

Nature 推薦的色盲友善配色（Wong 2011, Nature Methods）：

| 颜色 | Hex | RGB | 说明 |
|---|---|---|---|
| 黑 | `#000000` | 0,0,0 | 基準 |
| 橙 | `#E69F00` | 230,159,0 | 替代紅綠 |
| 天藍 | `#56B4E9` | 86,180,233 | 主要數據色 |
| 藍綠 | `#009E73` | 0,158,115 | |
| 黃 | `#F0E442` | 240,228,66 | |
| 藍 | `#0072B2` | 0,114,178 | |
| 朱紅 | `#D55E00` | 213,94,0 | 替代紅色 |
| 紫紅 | `#CC79A7` | 204,121,167 | 替代綠色 |

### Nature 明確避免清單

- ❌ 背景網格線（background gridlines）
- ❌ 多餘圖標和裝飾元素
- ❌ 陰影效果（drop shadows）
- ❌ 紋理花樣（patterns）
- ❌ 文字疊加在複雜圖片上
- ❌ 文字重疊
- ❌ 彩色列文字（改用 keylines + 黑色文字）
- ❌ CMYK 色彩空間（提交用 RGB，印製時自動轉 CMYK）
- ❌ 紅-綠配色方案

### 面板安排原則

- 字母順序排列（a, b, c...）
- 最小化白色空間
- 各面板大小依內容需求調整（不需要統一大小）

---

## The Lancet

來源：https://www.thelancet.com/ + Manusights formatting guide

### 顯示項目限制

| 文章類型 | 最多顯示項目 |
|---|---|
| Article | **5**（figures + tables 合計） |
| Review / Seminar | 6 |
| Comment | 1 |
| Correspondence | 1 |
| Viewpoint | 2 |

### 圖表規格

| 參數 | 要求 |
|---|---|
| 單欄寬度 | **79 mm** |
| 雙欄寬度 | **169 mm** |
| 最低解析度（光柵） | 300 DPI |
| 線條圖 | **1000 DPI** |
| 檔案格式 | TIFF, EPS, PDF, high-quality JPEG |
| 字體 | Arial / Helvetica, **8–10 pt** |

### 面板標籤

- **大寫字母（A, B, C）** — 注意：Nature 用小寫，Lancet 用大寫！
- 與 Nature 字體規範一致

### 表格特殊規則

- 必須用 Word 表格功能建立，不能是圖片
- **沒有垂直線**
- 水平線只在頂部、標題列下方、底部
- 腳註符號順序：\*, †, ‡, §

---

## Gemini Prompt 適用模板

當需要生成「符合期刊標準」的圖表時，在 prompt 中加入：

### Nature-style 修飾詞

```
Nature journal style, single column width (89mm equivalent), 
Arial font 5-7pt, panel labels (a/b/c) 8pt bold in upper-left corner,
RGB colour space, white background #FFFFFF,
Wong colorblind-safe palette (#E69F00 orange, #56B4E9 sky blue, #009E73 bluish green),
no gridlines, no drop shadows, no decorative icons,
all text in black, sans-serif, no outlined text,
clean minimal layout, publication-ready
```

### Lancet-style 修飾詞

```
The Lancet journal style, single column width (79mm equivalent),
Arial font 8-10pt, panel labels (A/B/C) bold uppercase,
white background, clean clinical layout,
no vertical lines in tables, horizontal lines only at top/header/bottom,
publication-ready figure quality
```

---

## 快速對照表：Nature vs Lancet

| 項目 | Nature | Lancet |
|---|---|---|
| 單欄寬度 | 89 mm | 79 mm |
| 雙欄寬度 | 183 mm | 169 mm |
| 面板標籤 | 小寫粗體 **a, b, c** | 大寫粗體 **A, B, C** |
| 字體大小 | 5–7 pt（面板 8pt） | 8–10 pt |
| 顯示上限 | 無明確上限 | 5（Article） |
| 偏好格式 | PDF / EPS / .ai | TIFF / EPS / PDF |
| 色彩空間 | RGB | RGB |
| 面板文字顏色 | 黑色 | 黑色 |

---

*Last updated: 2026-04-09*
