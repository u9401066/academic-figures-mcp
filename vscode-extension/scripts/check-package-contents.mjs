import { spawnSync } from "node:child_process";

const result = process.platform === "win32"
  ? spawnSync(process.env.ComSpec ?? "cmd.exe", ["/d", "/s", "/c", "npx vsce ls --no-dependencies"], {
    encoding: "utf8",
  })
  : spawnSync("npx", ["vsce", "ls", "--no-dependencies"], {
    encoding: "utf8",
  });

if (result.status !== 0) {
  process.stderr.write(result.stdout ?? "");
  process.stderr.write(result.stderr ?? "");
  if (result.error) {
    process.stderr.write(`${result.error.message}\n`);
  }
  process.exit(result.status ?? 1);
}

const files = new Set(
  result.stdout
    .split(/\r?\n/u)
    .map((line) => line.trim().replace(/\\/gu, "/"))
    .filter(Boolean),
);

const required = [
  "out/assistantAssets.js",
  "out/clineConfig.js",
  "out/codexConfig.js",
  "out/extension.js",
  "out/mcpProvider.js",
  "resources/repo-assets/academic-figures/AGENTS.md",
  "resources/repo-assets/academic-figures/.codex/skills/academic-figure-drawing-harness/SKILL.md",
  "resources/repo-assets/academic-figures/.codex/skills/asset-aware-mcp-harness/SKILL.md",
  "resources/repo-assets/academic-figures/.cline/skills/asset-aware-mcp-harness/SKILL.md",
  "resources/repo-assets/academic-figures/.clinerules/workflows/full-check.md",
  "resources/repo-assets/academic-figures/.github/agents/asset-aware-document.agent.md",
  "resources/repo-assets/academic-figures/.github/copilot-instructions.md",
];

const missing = required.filter((file) => !files.has(file));
if (missing.length > 0) {
  console.error("VSIX package contents are missing required harness files:");
  for (const file of missing) {
    console.error(`- ${file}`);
  }
  process.exit(1);
}

const forbidden = [
  ".asset-aware-mcp/",
  ".claude/",
  ".github/bylaws/",
  "node_modules/",
  "out/test/",
  "scripts/",
  "src/test/",
  "resources/repo-assets/academic-figures/.asset-aware-mcp/",
  "resources/repo-assets/academic-figures/.claude/",
  "resources/repo-assets/academic-figures/.github/bylaws/",
  "resources/repo-assets/academic-figures/scripts/",
];
const includedForbidden = [...files].filter((file) =>
  forbidden.some((forbiddenPath) => file === forbiddenPath || file.startsWith(forbiddenPath)),
);
if (includedForbidden.length > 0) {
  console.error("VSIX package contents include forbidden release artifacts:");
  for (const file of includedForbidden) {
    console.error(`- ${file}`);
  }
  process.exit(1);
}

const allowedRepoAssetRoots = [
  "resources/repo-assets/academic-figures/.cline/skills/",
  "resources/repo-assets/academic-figures/.clinerules/",
  "resources/repo-assets/academic-figures/.codex/skills/",
  "resources/repo-assets/academic-figures/.github/agents/",
];
const allowedRepoAssetFiles = new Set([
  "resources/repo-assets/academic-figures/AGENTS.md",
  "resources/repo-assets/academic-figures/.github/copilot-instructions.md",
]);
const unexpectedRepoAssets = [...files].filter((file) =>
  file.startsWith("resources/repo-assets/academic-figures/")
  && !allowedRepoAssetFiles.has(file)
  && !allowedRepoAssetRoots.some((root) => file.startsWith(root)),
);
if (unexpectedRepoAssets.length > 0) {
  console.error("VSIX package contents include unexpected bundled repo assets:");
  for (const file of unexpectedRepoAssets) {
    console.error(`- ${file}`);
  }
  process.exit(1);
}

console.log("VSIX package contents include bundled assistant harness assets.");
