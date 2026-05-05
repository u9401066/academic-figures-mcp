import fs from "fs";
import path from "path";

export type AssistantAssetInstallMode = "auto" | "manual";

export type AssistantAssetSummary = {
  installed: number;
  missingSources: string[];
  preserved: number;
  updated: number;
};

export type SyncAssistantAssetsOptions = {
  mode?: AssistantAssetInstallMode;
  sourceRoot: string;
  workspaceRoot: string;
};

const MANAGED_AGENTS_MARKERS = [
  "# Asset-Aware MCP Codex Harness",
  "These are workspace instructions for Codex when working with Asset-Aware MCP",
];
const MANAGED_COPILOT_MARKERS = [
  "Academic Figures MCP",
  "Asset-Aware MCP",
];

export function syncAssistantAssets(options: SyncAssistantAssetsOptions): AssistantAssetSummary {
  const summary: AssistantAssetSummary = {
    installed: 0,
    missingSources: [],
    preserved: 0,
    updated: 0,
  };

  syncManagedFile(
    path.join(options.sourceRoot, "AGENTS.md"),
    path.join(options.workspaceRoot, "AGENTS.md"),
    summary,
    {
      managedMarkers: MANAGED_AGENTS_MARKERS,
    },
  );
  syncManagedFile(
    path.join(options.sourceRoot, ".github", "copilot-instructions.md"),
    path.join(options.workspaceRoot, ".github", "copilot-instructions.md"),
    summary,
    {
      managedMarkers: MANAGED_COPILOT_MARKERS,
    },
  );

  syncDirectory(
    path.join(options.sourceRoot, ".codex", "skills"),
    path.join(options.workspaceRoot, ".codex", "skills"),
    summary,
    options.mode ?? "auto",
  );
  syncDirectory(
    path.join(options.sourceRoot, ".cline", "skills"),
    path.join(options.workspaceRoot, ".cline", "skills"),
    summary,
    options.mode ?? "auto",
  );
  syncDirectory(
    path.join(options.sourceRoot, ".clinerules"),
    path.join(options.workspaceRoot, ".clinerules"),
    summary,
    options.mode ?? "auto",
  );
  syncDirectory(
    path.join(options.sourceRoot, ".github", "agents"),
    path.join(options.workspaceRoot, ".github", "agents"),
    summary,
    options.mode ?? "auto",
  );

  return summary;
}

function syncManagedFile(
  sourcePath: string,
  destinationPath: string,
  summary: AssistantAssetSummary,
  options: { managedMarkers: readonly string[] },
): void {
  if (!fs.existsSync(sourcePath)) {
    summary.missingSources.push(sourcePath);
    return;
  }

  if (fs.existsSync(destinationPath)) {
    const current = fs.readFileSync(destinationPath, "utf8");
    const incoming = fs.readFileSync(sourcePath, "utf8");
    if (current === incoming) {
      return;
    }
    if (!isManagedContent(current, options.managedMarkers)) {
      summary.preserved++;
      return;
    }
    writeFile(destinationPath, incoming);
    summary.updated++;
    return;
  }

  copyFile(sourcePath, destinationPath);
  summary.installed++;
}

function syncDirectory(
  sourceRoot: string,
  destinationRoot: string,
  summary: AssistantAssetSummary,
  mode: AssistantAssetInstallMode,
): void {
  if (!fs.existsSync(sourceRoot)) {
    summary.missingSources.push(sourceRoot);
    return;
  }

  for (const sourcePath of collectFiles(sourceRoot)) {
    const destinationPath = path.join(destinationRoot, path.relative(sourceRoot, sourcePath));
    const incoming = fs.readFileSync(sourcePath, "utf8");
    if (fs.existsSync(destinationPath)) {
      const current = fs.readFileSync(destinationPath, "utf8");
      if (current === incoming) {
        continue;
      }
      if (mode === "auto") {
        summary.preserved++;
        continue;
      }
      writeFile(destinationPath, incoming);
      summary.updated++;
      continue;
    }

    writeFile(destinationPath, incoming);
    summary.installed++;
  }
}

function collectFiles(root: string): string[] {
  const files: string[] = [];
  const entries = fs.readdirSync(root, { withFileTypes: true })
    .sort((left, right) => left.name.localeCompare(right.name));

  for (const entry of entries) {
    const fullPath = path.join(root, entry.name);
    if (entry.isDirectory()) {
      files.push(...collectFiles(fullPath));
    } else if (entry.isFile()) {
      files.push(fullPath);
    }
  }

  return files;
}

function copyFile(sourcePath: string, destinationPath: string): boolean {
  const incoming = fs.readFileSync(sourcePath, "utf8");
  if (fs.existsSync(destinationPath) && fs.readFileSync(destinationPath, "utf8") === incoming) {
    return false;
  }
  writeFile(destinationPath, incoming);
  return true;
}

function writeFile(destinationPath: string, content: string): void {
  fs.mkdirSync(path.dirname(destinationPath), { recursive: true });
  fs.writeFileSync(destinationPath, content, "utf8");
}

function isManagedContent(content: string, markers: readonly string[]): boolean {
  return markers.some((marker) => content.includes(marker));
}
