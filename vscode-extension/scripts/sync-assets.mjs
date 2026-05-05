import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const scriptDir = path.dirname(fileURLToPath(import.meta.url));
const extensionRoot = path.resolve(scriptDir, "..");
const repoRoot = path.resolve(extensionRoot, "..");
const assetRoot = path.join(extensionRoot, "resources", "repo-assets", "academic-figures");

const assetFiles = [
  "AGENTS.md",
  ".github/copilot-instructions.md",
  ".github/agents/architect.agent.md",
  ".github/agents/ask.agent.md",
  ".github/agents/asset-aware-document.agent.md",
  ".github/agents/audit.agent.md",
  ".github/agents/code.agent.md",
  ".github/agents/context-loader.agent.md",
  ".github/agents/debug.agent.md",
  ".github/agents/deep-thinker.agent.md",
  ".github/agents/orchestrator.agent.md",
  ".github/agents/researcher.agent.md",
  ".github/agents/review-panel.agent.md",
  ".github/agents/reviewer-anthropic.agent.md",
  ".github/agents/reviewer-google.agent.md",
  ".github/agents/reviewer-openai.agent.md",
  ".github/agents/test-runner.agent.md",
  ".codex/skills/academic-figure-drawing-harness/SKILL.md",
  ".codex/skills/asset-aware-mcp-harness/SKILL.md",
  ".cline/skills/asset-aware-mcp-harness/SKILL.md",
  ".clinerules/00-project.md",
  ".clinerules/10-python.md",
  ".clinerules/20-vscode-extension.md",
  ".clinerules/30-citation-ready.md",
  ".clinerules/40-release.md",
  ".clinerules/workflows/full-check.md",
  ".clinerules/workflows/mcp-setup.md",
  ".clinerules/workflows/release-publish.md",
  ".clinerules/workflows/skills-audit.md",
];

function normalizeTextAsset(filePath) {
  const extension = path.extname(filePath).toLowerCase();
  const raw = fs.readFileSync(filePath);
  let content = raw[0] === 0xef && raw[1] === 0xbb && raw[2] === 0xbf
    ? raw.subarray(3)
    : raw;

  if ([".json", ".md", ".ps1", ".sh"].includes(extension)) {
    content = Buffer.from(content.toString("utf8").replace(/\r\n/g, "\n"), "utf8");
  }

  fs.writeFileSync(filePath, content);
}

function copyAsset(sourcePath, targetPath) {
  fs.mkdirSync(path.dirname(targetPath), { recursive: true });
  fs.copyFileSync(sourcePath, targetPath);
  normalizeTextAsset(targetPath);
}

fs.rmSync(assetRoot, { recursive: true, force: true });

for (const sourceRelative of assetFiles) {
  const sourcePath = path.join(repoRoot, ...sourceRelative.split("/"));
  const targetPath = path.join(assetRoot, ...sourceRelative.split("/"));
  if (!fs.existsSync(sourcePath)) {
    throw new Error(`Missing asset source: ${sourceRelative}`);
  }
  copyAsset(sourcePath, targetPath);
  console.log(`Synced ${sourceRelative} -> ${path.relative(extensionRoot, targetPath)}`);
}
