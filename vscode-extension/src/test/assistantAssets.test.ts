import assert from "node:assert/strict";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { afterEach, beforeEach, describe, it } from "node:test";

import { syncAssistantAssets } from "../assistantAssets";

describe("assistantAssets", () => {
  let tempRoot: string;
  let sourceRoot: string;
  let workspaceRoot: string;

  beforeEach(() => {
    tempRoot = fs.mkdtempSync(path.join(os.tmpdir(), "afm-assistant-assets-"));
    sourceRoot = path.join(tempRoot, "source");
    workspaceRoot = path.join(tempRoot, "workspace");
    writeAsset("AGENTS.md", "# Asset-Aware MCP Codex Harness\n");
    writeAsset(".codex/skills/academic-figure-drawing-harness/SKILL.md", "# Drawing\n");
    writeAsset(".codex/skills/asset-aware-mcp-harness/SKILL.md", "# Harness\n");
    writeAsset(".cline/skills/asset-aware-mcp-harness/SKILL.md", "# Cline Harness\n");
    writeAsset(".clinerules/00-project.md", "# Project Rules\n");
    writeAsset(".github/copilot-instructions.md", "# Academic Figures MCP Copilot Instructions\n");
    writeAsset(".github/agents/asset-aware-document.agent.md", "# Agent\n");
  });

  afterEach(() => {
    fs.rmSync(tempRoot, { recursive: true, force: true });
  });

  it("installs bundled Codex, Cline, Copilot, and rule assets into a workspace", () => {
    const summary = syncAssistantAssets({ sourceRoot, workspaceRoot, mode: "auto" });

    assert.equal(summary.missingSources.length, 0);
    assert.ok(summary.installed > 0);
    assert.equal(readWorkspace("AGENTS.md"), "# Asset-Aware MCP Codex Harness\n");
    assert.equal(readWorkspace(".codex/skills/academic-figure-drawing-harness/SKILL.md"), "# Drawing\n");
    assert.equal(readWorkspace(".cline/skills/asset-aware-mcp-harness/SKILL.md"), "# Cline Harness\n");
    assert.equal(readWorkspace(".clinerules/00-project.md"), "# Project Rules\n");
    assert.equal(readWorkspace(".github/copilot-instructions.md"), "# Academic Figures MCP Copilot Instructions\n");
    assert.equal(readWorkspace(".github/agents/asset-aware-document.agent.md"), "# Agent\n");
  });

  it("preserves custom AGENTS.md while still installing managed skills", () => {
    writeWorkspace("AGENTS.md", "# My local Codex rules\n");

    const summary = syncAssistantAssets({ sourceRoot, workspaceRoot, mode: "auto" });

    assert.equal(readWorkspace("AGENTS.md"), "# My local Codex rules\n");
    assert.equal(readWorkspace(".codex/skills/academic-figure-drawing-harness/SKILL.md"), "# Drawing\n");
    assert.equal(summary.preserved, 1);
  });

  it("does not overwrite existing directory assets during automatic activation sync", () => {
    writeWorkspace(".codex/skills/asset-aware-mcp-harness/SKILL.md", "# Local Codex Skill\n");
    writeWorkspace(".clinerules/00-project.md", "# Local Rule\n");
    writeWorkspace(".github/agents/asset-aware-document.agent.md", "# Local Agent\n");

    const summary = syncAssistantAssets({ sourceRoot, workspaceRoot, mode: "auto" });

    assert.equal(
      readWorkspace(".codex/skills/asset-aware-mcp-harness/SKILL.md"),
      "# Local Codex Skill\n",
    );
    assert.equal(readWorkspace(".clinerules/00-project.md"), "# Local Rule\n");
    assert.equal(readWorkspace(".github/agents/asset-aware-document.agent.md"), "# Local Agent\n");
    assert.equal(summary.preserved, 3);
  });

  function writeAsset(relativePath: string, content: string): void {
    const target = path.join(sourceRoot, ...relativePath.split("/"));
    fs.mkdirSync(path.dirname(target), { recursive: true });
    fs.writeFileSync(target, content, "utf8");
  }

  function writeWorkspace(relativePath: string, content: string): void {
    const target = path.join(workspaceRoot, ...relativePath.split("/"));
    fs.mkdirSync(path.dirname(target), { recursive: true });
    fs.writeFileSync(target, content, "utf8");
  }

  function readWorkspace(relativePath: string): string {
    return fs.readFileSync(path.join(workspaceRoot, ...relativePath.split("/")), "utf8");
  }
});
