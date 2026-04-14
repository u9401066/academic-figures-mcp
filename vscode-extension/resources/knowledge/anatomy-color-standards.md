# Anatomy Color Standards — 醫學插圖色彩規範

> 研究日期：2026-04-08 | 來源：medizinische-illustration.ch, kenhub.com, Netter/Gray's/Thieme atlases cross-reference
> **注意：** 沒有正式 AAAMI 機器可讀色碼文件；以下為跨 atlas 事實標準

---

## 核心原理：功能性符号，非寫實

> 「顏色編碼的目的是幫助讀者快速辨識結構類型，而非精確還原組織真實顏色」
> — medizinische-illustration.ch

- 人體解剖天然以紅色（肌肉）和米色（結締組織）為主，缺乏天然色彩對比
- **越缺乏形狀/紋理特徵的結構（血管、神經），越需要強烈顏色對比** 來協助視覺辨識
- 有明顯形狀的結構（大腸、骨骼）顏色慣例反而較少

---

## 標準色彩映射表（跨 Netter / Gray's / Thieme 一致）

| 結構類型 | 標準色 Hex | 視覺描述 | 顏色理由 |
|---------|-----------|---------|---------|
| **Artery（arterial）** | `#FF2200`（飽和紅，高光澤）| 鮮紅帶高光 | 含氧血較鮮紅；與藍色靜脈形成強烈互補色對比；形狀與靜脈相似需靠顏色區分 |
| **Vein（venous）** | `#4040A0`（深藍紫）| 深藍紫 | 去氧血較暗；視覺上與artery形成互補色對；形狀與artery相似需靠顏色區分 |
| **Nerve（神經）** | `#E8C330`（標準黃）或 `#F5D800` | 明亮黃色 | 細長走行難以形狀辨認；歷史慣例非常穩定，各 atlas 一致；亮黃確保神經束在複雜區域可見 |
| **Muscle（肌肉）** | `#8B0000`–`#C00000`（深紅棕）| 深紅棕，帶纖維紋理 | 避免與artery紅衝突；肉品氧化後褐色的觀念；比artery暗且無光澤 |
| **Bone（骨骼）** | `#F5F0E0`（米白/象牙色）| 米白 | 接近真實骨骼色；周圍軟組織襯托下自然可見 |
| **Lymphatic vessel（淋巴管）** | `#50C878`（翠綠）或 `#3CB371` | 綠色 | 與紅（artery）和藍（vein）形成第三套顏色通道；淋巴系統獨立於血管系統 |
| **Lymph node（淋巴結）** | `#228B22`（森林綠）| 深綠色豆形 | 淋巴結通常描述為豆形/腎形，綠色區分於血管 |
| **Fat（脂肪組織）** | `#FFD700`–`#FFA500`（黃橙）| 顆粒狀黃橙色 | 接近手術暴露時的真實顏色（黃色脂肪）；顆粒狀紋理幫助與肌肉區分 |
| **Fascia（筋膜）** | `#E8E8E8`（半透明白/銀白）| 半透明銀白纖維層 | 真實筋膜為白色纖維組織；30-50% opacity 表現輕薄感；包裹結構時需可透視底層 |
| **Cartilage（軟骨）** | `#B0C4DE`（淡藍灰）或 `#F0F8FF` | 淡藍灰/珍珠白 | 半透明感，與骨頭和肌肉均不同；關節軟骨呈淡藍白色 |
| **Skin（皮膚）** | `#EECBA0`–`#D4A574`（自然肤色）| 淺棕/淺米色 | 接近真實皮膚色；可根據種族調整 |
| **Blood（血液）** | `#CC0000`（深紅）| 深紅 | 血液無論動靜脈在插圖中通常統一為深紅；除非需要特意區分才分色 |
| **Tendon（肌腱）** | `#D4C4A8`（淡黃白）| 淡黃白，緊密纖維束 | 接近真实肌腱色（銀白色）；比肌肉更白/緊密 |

---

## Prompt 技巧（可直接使用）

### 技巧 A — 明確迴避顏色衝突

```
Muscles in deep crimson red (#8B0000) with fiber texture, 
NOT bright saturated red — avoid conflict with artery red which is brighter
```

### 技巧 B — 加入顏色理由提升遵從度

```
Arteries: saturated glossy red because they carry oxygenated blood 
and must be immediately distinguishable from veins
Veins: deep blue-purple because they carry deoxygenated blood
```

### 技巧 C — 筋膜透明度描述

```
Fascia as thin translucent white-silver sheet (30-50% opacity) 
wrapping around structures, fibrous weave texture visible
```

### 技巧 D — 多結構系統顏色分組

```
Color coding for this neurovasculature diagram:
- Arteries: saturated red (#FF2200)
- Veins: deep blue-purple (#4040A0)
- Nerves: bright yellow (#E8C330)
- Arteries and nerves should be visibly distinct from each other
```

### 技巧 E — 避免常見錯誤

- **靜脈不是藍色**：實際為暗紅色，藍色是為了對比artery的慣例符號
- **肌肉不是亮紅色**：肌肉是深紅棕，artery的紅更亮/更飽和
- **骨骼不是純白色**：象牙色/米白，純白會與標籤/白底衝突

---

## 常見失敗模式與修復

| 問題 | 原因 | 修復方式 |
|------|------|---------|
| Artery 和 Muscle 都是紅色分不清 | Prompt 未指定差異 | 明確：「artery brighter, glossy red; muscle darker, matte deep red」|
| 靜脈看起來像artery | 未指定藍色 vs 紅色 | 「veins must be visually distinguishable from arteries by using blue-purple」|
| 神經和脂肪都是黃色 | 未指定神經應為亮黃 | 「nerves: bright saturated yellow (#E8C330), fat: pale orange-yellow, clearly different saturation」|
| 筋膜變成實心白色 | 未指定透明度 | 「fascia: translucent white, 30-50% opacity, fibrous texture visible」|

---

## 參考來源

- [medizinische-illustration.ch — Colour Codes in medical illustration](https://www.medizinische-illustration.ch/post/colour-codes)
- [Kenhub — Major arteries, veins and nerves of the body](https://www.kenhub.com/en/library/anatomy/major-arteries-veins-and-nerves-of-the-body)
- Netter's Atlas of Human Anatomy（事實標準）
- Gray's Anatomy（學術標準）
- SAM Medical illustration color scheme（PDF, scribd.com）
