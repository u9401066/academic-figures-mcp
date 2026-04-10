# Product Context

## Overview

Academic Figures MCP is a workflow-oriented MCP product for turning academic intent, paper metadata, style constraints, and revision feedback into publication-ready visual outputs.

## Core Features

- MCP-orchestrated planning, generation, evaluation, and iteration for academic visual assets.
- Generic payload-based rendering with journal-aware prompt injection from a YAML registry.
- Planned poster-generation workflow with larger-layout composition.
- Planned grouped multi-panel figure generation.
- Planned montage/composite assembly that combines multiple source images into one master figure.
- Planned journal retargeting for an existing image without restarting concept design from zero.
- Planned prompt persistence and replay for reproducible outputs.
- Planned style extraction from an existing image back into a reusable style prompt.

## Technical Stack

- Python 3.10+
- FastMCP / MCP
- VS Code extension host
- Google Gemini
- OpenRouter
- PubMed E-utilities
- PyYAML

## Project Description

Academic Figures MCP is an agent harness that orchestrates the full academic-figure generation workflow: paper ingestion, figure planning, prompt building, image generation, evaluation, and iteration. MCP integration and VS Code extension packaging are core product surfaces for making the workflow accessible to non-engineers.

## Architecture

The system should be communicated as a workflow-oriented MCP product with a packaged VSX front end, where provider integrations such as Google Gemini or OpenRouter are replaceable infrastructure behind the harness. The runtime is centered on a Python MCP server for planning, rendering, evaluation, and reusable job artifacts, with the VS Code extension acting as the local operator surface.

## Technologies

- Python
- Model Context Protocol (MCP)
- VS Code Extension (VSX)
- Google Gemini
- OpenRouter
- PubMed E-utilities
- YAML-based configuration and style registries

## Libraries and Dependencies

- mcp[cli]>=1.27.0
- httpx>=0.27.0
- google-genai>=1.0.0
- pillow>=10.0
- pyyaml>=6.0
- uv
