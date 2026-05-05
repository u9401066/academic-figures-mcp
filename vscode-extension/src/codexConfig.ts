import fs from "fs";
import os from "os";
import path from "path";

export type CodexServerSpec = {
  command: string;
  args: string[];
  env?: Record<string, string>;
};

export type AcademicFiguresCodexSpecOptions = {
  env?: Record<string, string>;
  packageName: string;
  version?: string;
};

export type InstallCodexOptions = {
  force?: boolean;
};

const ACADEMIC_FIGURES_SERVER_KEY = "academic-figures";
const LEGACY_SERVER_KEYS = ["academic-figures-mcp", "academicFigures"] as const;
const MANAGED_COMMENT =
  "# Managed by Academic Figures MCP VS Code extension. Remove this block to opt out.";

export function getCodexHome(): string {
  const override = process.env.CODEX_HOME?.trim();
  return override || path.join(os.homedir(), ".codex");
}

export function getCodexConfigPath(): string {
  return path.join(getCodexHome(), "config.toml");
}

export function buildAcademicFiguresCodexServerSpec(
  options: AcademicFiguresCodexSpecOptions,
): CodexServerSpec {
  const packageRef = options.version
    ? `${options.packageName}==${options.version}`
    : options.packageName;
  return {
    command: "uvx",
    args: ["--from", packageRef, "afm-server"],
    env: options.env ?? {},
  };
}

export function installCodexMcpServer(
  spec: CodexServerSpec,
  options: InstallCodexOptions = {},
): boolean {
  if (!options.force && !fs.existsSync(getCodexHome())) {
    return false;
  }

  const configPath = getCodexConfigPath();
  const original = readConfig(configPath);
  let content = original;
  for (const serverKey of [ACADEMIC_FIGURES_SERVER_KEY, ...LEGACY_SERVER_KEYS]) {
    content = stripManagedBlock(content, serverKey).content;
  }
  if (hasServerBlock(content, ACADEMIC_FIGURES_SERVER_KEY)) {
    return false;
  }
  let next = ensureTrailingBlankLine(content);
  next += `${MANAGED_COMMENT}\n${renderManagedBlock(ACADEMIC_FIGURES_SERVER_KEY, spec)}`;

  if (next === original) {
    return false;
  }

  writeConfigAtomic(configPath, next);
  return true;
}

function renderManagedBlock(serverKey: string, spec: CodexServerSpec): string {
  const lines = [
    `[mcp_servers.${serverKey}]`,
    `command = "${escapeTomlString(spec.command)}"`,
    `args = ${renderTomlArray(spec.args)}`,
  ];
  const env = spec.env ?? {};
  const envKeys = Object.keys(env)
    .filter((key) => env[key] !== "")
    .sort();

  if (envKeys.length > 0) {
    lines.push("", `[mcp_servers.${serverKey}.env]`);
    for (const key of envKeys) {
      lines.push(`${key} = "${escapeTomlString(env[key])}"`);
    }
  }

  return `${lines.join("\n")}\n`;
}

function stripManagedBlock(
  content: string,
  serverKey: string,
): { content: string; removed: boolean } {
  const lines = content.split(/\r?\n/u);
  const output: string[] = [];
  let removed = false;
  let index = 0;

  while (index < lines.length) {
    const line = lines[index];
    if (line.trim() === MANAGED_COMMENT) {
      const headerIndex = findNextNonBlankLine(lines, index + 1);
      if (
        headerIndex !== undefined
        && managedHeaderPattern(serverKey).test(lines[headerIndex])
      ) {
        removed = true;
        index = findManagedBlockEnd(lines, headerIndex, serverKey);
        while (output.length > 0 && output[output.length - 1].trim() === "") {
          output.pop();
        }
        continue;
      }
    }

    output.push(line);
    index++;
  }

  return {
    content: output.join("\n").replace(/\n{3,}$/u, "\n\n"),
    removed,
  };
}

function findNextNonBlankLine(lines: string[], startIndex: number): number | undefined {
  for (let index = startIndex; index < lines.length; index++) {
    if (lines[index].trim() !== "") {
      return index;
    }
  }
  return undefined;
}

function findManagedBlockEnd(lines: string[], startIndex: number, serverKey: string): number {
  const headerRe = managedHeaderPattern(serverKey);
  const anyHeaderRe = /^\s*\[\s*[^\]]+\s*\]\s*$/u;
  let index = startIndex;
  while (index < lines.length) {
    const line = lines[index];
    if (anyHeaderRe.test(line) && !headerRe.test(line)) {
      break;
    }
    index++;
  }
  return index;
}

function hasServerBlock(content: string, serverKey: string): boolean {
  const headerRe = managedHeaderPattern(serverKey);
  return content.split(/\r?\n/u).some((line) => headerRe.test(line));
}

function managedHeaderPattern(serverKey: string): RegExp {
  const escaped = serverKey.replace(/[.*+?^${}()|[\]\\]/gu, "\\$&");
  return new RegExp(`^\\s*\\[\\s*mcp_servers\\.${escaped}(?:\\.[^\\]]+)?\\s*\\]\\s*$`, "u");
}

function ensureTrailingBlankLine(content: string): string {
  if (!content) {
    return "";
  }
  if (content.endsWith("\n\n")) {
    return content;
  }
  if (content.endsWith("\n")) {
    return `${content}\n`;
  }
  return `${content}\n\n`;
}

function readConfig(configPath: string): string {
  if (!fs.existsSync(configPath)) {
    return "";
  }
  return fs.readFileSync(configPath, "utf8");
}

function writeConfigAtomic(configPath: string, content: string): void {
  fs.mkdirSync(path.dirname(configPath), { recursive: true });
  const tempPath = `${configPath}.tmp.${Date.now()}`;
  fs.writeFileSync(tempPath, content, "utf8");
  fs.renameSync(tempPath, configPath);
}

function renderTomlArray(values: string[]): string {
  return `[${values.map((value) => `"${escapeTomlString(value)}"`).join(", ")}]`;
}

function escapeTomlString(value: string): string {
  return value
    .replace(/\\/gu, "\\\\")
    .replace(/"/gu, '\\"')
    .replace(/\n/gu, "\\n")
    .replace(/\r/gu, "\\r")
    .replace(/\t/gu, "\\t");
}

export const __test__ = {
  stripManagedBlock,
  renderManagedBlock,
  escapeTomlString,
};
