import fs from "fs";
import path from "path";

export type ClineServerEntry = {
  alwaysAllow?: string[];
  args: string[];
  command: string;
  disabled?: boolean;
  env?: Record<string, string>;
  [key: string]: unknown;
};

type ClineSettings = {
  mcpServers: Record<string, ClineServerEntry>;
};

type ClineSpecOptions = {
  env?: Record<string, string>;
  packageName: string;
  version?: string;
};

const CLINE_EXTENSION_ID = "saoudrizwan.claude-dev";
const CLINE_SERVER_KEY = "academic-figures";
const LEGACY_SERVER_KEYS = ["academic-figures-mcp", "academicFigures"] as const;

export function getClineMcpSettingsPath(extensionGlobalStoragePath: string): string {
  return path.join(
    path.dirname(extensionGlobalStoragePath),
    CLINE_EXTENSION_ID,
    "settings",
    "cline_mcp_settings.json",
  );
}

export function isClineSettingsAvailable(extensionGlobalStoragePath: string): boolean {
  return fs.existsSync(path.dirname(path.dirname(getClineMcpSettingsPath(extensionGlobalStoragePath))));
}

export function buildAcademicFiguresClineServerEntry(options: ClineSpecOptions): ClineServerEntry {
  const packageRef = options.version
    ? `${options.packageName}==${options.version}`
    : options.packageName;
  return {
    command: "uvx",
    args: ["--from", packageRef, "afm-server"],
    disabled: false,
    env: options.env ?? {},
  };
}

export function installClineMcpServer(settingsPath: string, entry: ClineServerEntry): boolean {
  const settings = readClineSettings(settingsPath);
  if (!settings) {
    return false;
  }

  const original = JSON.stringify(settings, null, 2);
  const existing = settings.mcpServers[CLINE_SERVER_KEY];
  if (existing && !isManagedEntry(existing)) {
    return false;
  }
  const next = mergeClineEntry(existing, entry);
  settings.mcpServers[CLINE_SERVER_KEY] = next;

  for (const legacyKey of LEGACY_SERVER_KEYS) {
    if (isManagedEntry(settings.mcpServers[legacyKey])) {
      delete settings.mcpServers[legacyKey];
    }
  }

  const rendered = `${JSON.stringify(settings, null, 2)}\n`;
  if (`${original}\n` === rendered) {
    return false;
  }

  writeClineSettings(settingsPath, rendered);
  return true;
}

function mergeClineEntry(
  existing: ClineServerEntry | undefined,
  next: ClineServerEntry,
): ClineServerEntry {
  if (!existing || !isManagedEntry(existing)) {
    return next;
  }

  return {
    ...existing,
    ...next,
    alwaysAllow: existing.alwaysAllow,
    disabled: existing.disabled ?? next.disabled,
  };
}

function readClineSettings(settingsPath: string): ClineSettings | undefined {
  if (!fs.existsSync(settingsPath)) {
    return { mcpServers: {} };
  }

  try {
    const parsed = JSON.parse(fs.readFileSync(settingsPath, "utf8")) as Partial<ClineSettings>;
    return {
      ...parsed,
      mcpServers: typeof parsed.mcpServers === "object" && parsed.mcpServers
        ? parsed.mcpServers
        : {},
    };
  } catch {
    return undefined;
  }
}

function writeClineSettings(settingsPath: string, content: string): void {
  fs.mkdirSync(path.dirname(settingsPath), { recursive: true });
  const tempPath = `${settingsPath}.tmp.${Date.now()}.json`;
  fs.writeFileSync(tempPath, content, "utf8");
  fs.renameSync(tempPath, settingsPath);
}

function isManagedEntry(entry: ClineServerEntry | undefined): boolean {
  return Boolean(entry?.args?.includes("afm-server"));
}
