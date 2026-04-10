---
description: "Evaluate an academic figure using 8-domain quality checklist"
---
# Evaluate Academic Figure

Evaluate an existing academic figure against the 8-domain quality checklist.

## Steps

1. Confirm the image file path exists.
2. Use the `evaluate_figure` MCP tool with the image path.
3. Optionally pass `figure_type` for domain-specific evaluation.
4. Optionally pass `reference_pmid` to check citation accuracy.
5. Present the evaluation results with per-domain scores and suggestions.

## Evaluation Domains

1. **Text accuracy** — Are all labels, numbers, and citations correct?
2. **Anatomy** — Are anatomical structures correctly depicted?
3. **Color** — Does the palette follow journal/accessibility standards?
4. **Layout** — Is the visual hierarchy clear and balanced?
5. **Scientific accuracy** — Does the content match the paper's findings?
6. **Legibility** — Can all text be read at publication size?
7. **Visual polish** — Is the figure free of artifacts and well-composed?
8. **Citation** — Are PMID, authors, and journal properly attributed?

## Example

```
User: 評估一下這張圖 outputs/38106543_flowchart.png
→ evaluate_figure(image_path="outputs/38106543_flowchart.png", figure_type="flowchart")
```
