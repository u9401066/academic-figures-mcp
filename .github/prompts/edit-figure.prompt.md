---
description: "Edit an existing academic figure with natural language instructions"
---
# Edit Academic Figure

Refine an existing academic figure using natural language feedback.

## Steps

1. Confirm the source image file exists.
2. Translate user's editing intent into a clear instruction.
3. Use the `edit_figure` MCP tool with the image path and feedback.
4. Review the edit result and check if the changes match expectations.
5. If unsatisfied, suggest further refinements.

## Supported Edit Types

- **Color changes**: "箭頭改紅色", "背景改白色"
- **Text edits**: "標題字大一點", "Add PMID in footer"
- **Layout tweaks**: "把左邊的方塊移到右邊"
- **Style conversion**: "改成 Nature 風格"
- **Element additions**: "加上圖例", "加上比例尺"

## Example

```
User: 把這張圖的箭頭都改成紅色
→ edit_figure(image_path="outputs/xxx.png", feedback="把所有箭頭改成紅色")
```
