# Generate Your First Figure

Now you're ready to create publication-ready scientific figures!

## Try These Prompts in Copilot Chat

```text
Generate a figure for PMID 41657234
```

```text
Create a drug mechanism diagram for propofol
```

```text
Make a Netter-like airway anatomy illustration
```

## How It Works

1. **Plan**: The MCP server resolves the best figure type, rendering route, and presets
2. **Generate**: The selected provider generates the image
3. **Evaluate**: Use the 8-domain rubric to assess quality
4. **Iterate**: Transform style or regenerate with feedback

## OpenRouter Example

If you selected OpenRouter, the extension can launch the server with:

- `AFM_IMAGE_PROVIDER=openrouter`
- `OPENROUTER_API_KEY=...`
- `GEMINI_MODEL=google/gemini-3.1-flash-image-preview`

## Browse Presets

Open the **Academic Figures** sidebar (activity bar icon) to explore:

- **Journal Presets**: Nature, Lancet, Review Infographic
- **Visual Styles**: Netter-like, Flat Infographic, Clean Schematic
- **Domain Presets**: Drug Mechanism, Airway Anatomy, Clinical Workflow
- **Rendering Routes**: image_generation, code_render_matplotlib, SVG, D2, Mermaid
