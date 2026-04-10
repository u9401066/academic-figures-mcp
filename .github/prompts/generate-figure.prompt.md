---
description: "Generate a publication-ready academic figure from a PubMed paper"
---
# Generate Academic Figure

Given a PubMed ID (PMID), generate a publication-ready academic figure.

## Steps

1. Use the `generate_figure` MCP tool with the provided PMID.
2. If the user specifies a figure type (flowchart, mechanism, comparison, anatomical, timeline, statistical), pass it. Otherwise use "auto".
3. Default language is "zh-TW" (Traditional Chinese) unless specified otherwise.
4. Review the returned metadata (figure_type, template, model, prompt_length).
5. If the result status is not "ok", explain the error and suggest fixes.

## Example

```
User: 幫我把 PMID 12345678 做成流程圖
→ generate_figure(pmid="12345678", figure_type="flowchart", language="zh-TW")
```

## Output Expectations

- PNG image saved to `.academic-figures/outputs/`
- Metadata includes: figure_type, template, model, elapsed_seconds
- 7-block prompt structure: Title, Layout, Elements, Color, Text, Style, Size
