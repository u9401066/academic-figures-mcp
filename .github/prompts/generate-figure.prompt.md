---
description: "Generate a publication-ready academic figure from a PMID, preprint, repo, or research brief"
---
# Generate Academic Figure

Given a PMID, preprint brief, repository brief, or research concept, generate a publication-ready academic figure.

## Steps

1. Prefer calling `generate_figure` directly as the default entrypoint.
2. If the user provides a PMID, pass it as `pmid`.
3. If the user provides a preprint, repo, or generic brief, pass `source_title` and use `source_kind` such as `preprint`, `repo`, or `brief`. Add `source_summary` and `source_identifier` when available.
4. If the user specifies a figure type (flowchart, mechanism, comparison, anatomical, timeline, statistical), pass it. Otherwise use "auto".
5. If the user asks for a delivered file type such as PNG, JPEG, or WebP, pass `output_format`.
6. Default language is "zh-TW" (Traditional Chinese) unless specified otherwise.
7. Review the returned metadata (figure_type, template, model, prompt_length).
8. Only call `plan_figure` separately when the host explicitly wants to inspect or edit the planning payload before rendering.
9. If the result status is not "ok", explain the error and suggest fixes.

## Example

```
User: 幫我把 PMID 12345678 做成流程圖
→ generate_figure(pmid="12345678", figure_type="flowchart", language="zh-TW")

User: 幫我把這個 GitHub repo 做成架構總覽圖
→ generate_figure(source_title="HyperHierarchicalRAG repository overview", source_kind="repo", source_identifier="https://github.com/zzstoatzz/HyperHierarchicalRAG", source_summary="Explain the retrieval hierarchy, orchestration, and system boundaries.", language="zh-TW")
```

## Output Expectations

- PNG image saved to `.academic-figures/outputs/`
- Metadata includes: figure_type, template, model, elapsed_seconds
- 7-block prompt structure: Title, Layout, Elements, Color, Text, Style, Size
