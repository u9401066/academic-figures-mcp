# Configure a Connection

The extension supports **two runtime image providers**:

- **Google Gemini** using `GOOGLE_API_KEY`
- **OpenRouter** using `OPENROUTER_API_KEY`

You can now choose **how** the extension loads credentials:

- **VS Code SecretStorage**
- **An env file path** such as `.vscode/academic-figures.env`
- **The current process environment**

## Get Your API Key

### Google Gemini

1. Visit [Google AI Studio](https://aistudio.google.com/apikey)
2. Click **Create API Key**
3. Copy the key

### OpenRouter

1. Visit [OpenRouter Keys](https://openrouter.ai/keys)
2. Create a key
3. Use model `google/gemini-3.1-flash-image-preview`

## Configure in VS Code

Run **Academic Figures: Configure Connection** to open the menu-driven setup flow.

From the same menu you can:

- Paste a Google or OpenRouter key into SecretStorage
- Paste or browse to an env file path
- Generate a new env template for Google, OpenRouter, or Ollama-style local settings
- Save OpenRouter base URL and header settings
- Save Ollama endpoint and model settings for local or future tooling

> **Runtime note**: Academic Figures image generation currently runs through Google Gemini or OpenRouter. Ollama settings are stored by the extension, but the Python server does not use them yet.
