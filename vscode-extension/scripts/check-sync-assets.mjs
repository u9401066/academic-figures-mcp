import { createHash } from "node:crypto";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { fileURLToPath } from "node:url";

const scriptDir = path.dirname(fileURLToPath(import.meta.url));
const extensionRoot = path.resolve(scriptDir, "..");
const repoRoot = path.resolve(extensionRoot, "..");
const assetRoot = path.join(extensionRoot, "resources", "repo-assets", "academic-figures");
const expectedRoot = fs.mkdtempSync(path.join(os.tmpdir(), "afm-sync-assets-"));

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

function snapshotDirectory(root) {
  const snapshot = new Map();
  if (!fs.existsSync(root)) {
    return snapshot;
  }

  function normalizedContent(filePath) {
    const raw = fs.readFileSync(filePath);
    let content = raw[0] === 0xef && raw[1] === 0xbb && raw[2] === 0xbf
      ? raw.subarray(3)
      : raw;
    if ([".json", ".md", ".ps1", ".sh"].includes(path.extname(filePath).toLowerCase())) {
      content = Buffer.from(content.toString("utf8").replace(/\r\n/g, "\n"), "utf8");
    }
    return content;
  }

  function walk(directory) {
    for (const entry of fs.readdirSync(directory, { withFileTypes: true })
      .sort((left, right) => left.name.localeCompare(right.name))) {
      const fullPath = path.join(directory, entry.name);
      if (entry.isDirectory()) {
        walk(fullPath);
        continue;
      }
      if (!entry.isFile()) {
        continue;
      }
      const relativePath = path.relative(root, fullPath).replaceAll(path.sep, "/");
      const hash = createHash("sha256").update(normalizedContent(fullPath)).digest("hex");
      snapshot.set(relativePath, hash);
    }
  }

  walk(root);
  return snapshot;
}

function diffSnapshots(actual, expected) {
  const changes = [];
  const paths = new Set([...actual.keys(), ...expected.keys()]);
  for (const relativePath of [...paths].sort()) {
    if (!actual.has(relativePath)) {
      changes.push(`missing ${relativePath}`);
    } else if (!expected.has(relativePath)) {
      changes.push(`stale ${relativePath}`);
    } else if (actual.get(relativePath) !== expected.get(relativePath)) {
      changes.push(`changed ${relativePath}`);
    }
  }
  return changes;
}

try {
  for (const sourceRelative of assetFiles) {
    const sourcePath = path.join(repoRoot, ...sourceRelative.split("/"));
    const targetPath = path.join(expectedRoot, ...sourceRelative.split("/"));
    if (!fs.existsSync(sourcePath)) {
      console.error(`Missing asset source: ${sourceRelative}`);
      process.exit(1);
    }
    copyAsset(sourcePath, targetPath);
  }

  const changes = diffSnapshots(
    snapshotDirectory(assetRoot),
    snapshotDirectory(expectedRoot),
  );
  if (changes.length > 0) {
    console.error("Assistant assets are not synchronized with source files.");
    for (const change of changes.slice(0, 50)) {
      console.error(`- ${change}`);
    }
    if (changes.length > 50) {
      console.error(`...and ${changes.length - 50} more`);
    }
    process.exit(1);
  }

  console.log("Assistant assets are synchronized.");
} finally {
  fs.rmSync(expectedRoot, { recursive: true, force: true });
}

function copyAsset(sourcePath, targetPath) {
  fs.mkdirSync(path.dirname(targetPath), { recursive: true });
  fs.copyFileSync(sourcePath, targetPath);
  normalizeTextAsset(targetPath);
}

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
