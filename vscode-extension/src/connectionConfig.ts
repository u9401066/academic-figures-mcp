import * as fs from "fs";
import * as path from "path";

export const GOOGLE_PROVIDER = "google";
export const OPENROUTER_PROVIDER = "openrouter";
export const OPENAI_PROVIDER = "openai";
export const OLLAMA_PROVIDER = "ollama";

export const SECRET_STORAGE_SOURCE = "secretStorage";
export const ENV_FILE_SOURCE = "envFile";
export const PROCESS_ENV_SOURCE = "processEnv";

export const DEFAULT_GOOGLE_MODEL = "gemini-3.1-flash-image-preview";
export const DEFAULT_OPENROUTER_MODEL = "google/gemini-3.1-flash-image-preview";
export const DEFAULT_OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1";
export const DEFAULT_OPENROUTER_REFERER = "https://github.com/u9401066/academic-figures-mcp";
export const DEFAULT_OPENROUTER_TITLE = "Academic Figures MCP";
export const DEFAULT_OPENAI_MODEL = "gpt-image-2";
export const DEFAULT_OPENAI_BASE_URL = "https://api.openai.com/v1";
export const DEFAULT_OPENAI_VISION_MODEL = "gpt-5.4-mini";
export const DEFAULT_OPENAI_IMAGE_SIZE = "auto";
export const DEFAULT_OLLAMA_BASE_URL = "http://localhost:11434/v1";
export const DEFAULT_OLLAMA_MODEL = "llava:latest";
export const DEFAULT_ENVIRONMENT_FILE = ".vscode/academic-figures.env";

export function getSupportedImageProvider(provider: string): string {
  if (provider === OPENROUTER_PROVIDER || provider === OPENAI_PROVIDER || provider === OLLAMA_PROVIDER) {
    return provider;
  }
  return GOOGLE_PROVIDER;
}

export function getApiKeyEnvName(provider: string): string {
  if (provider === OPENROUTER_PROVIDER) {
    return "OPENROUTER_API_KEY";
  }
  if (provider === OPENAI_PROVIDER) {
    return "OPENAI_API_KEY";
  }
  if (provider === OLLAMA_PROVIDER) {
    return "OLLAMA_BASE_URL / OLLAMA_MODEL";
  }
  return "GOOGLE_API_KEY";
}

export function resolveEnvironmentFilePath(workspaceRoot: string | undefined, configuredPath: string): string {
  const trimmed = configuredPath.trim();
  if (!trimmed) {
    return workspaceRoot
      ? path.join(workspaceRoot, DEFAULT_ENVIRONMENT_FILE)
      : path.resolve(process.cwd(), DEFAULT_ENVIRONMENT_FILE);
  }
  if (path.isAbsolute(trimmed)) {
    return path.normalize(trimmed);
  }
  return path.join(workspaceRoot ?? process.cwd(), trimmed);
}

export function toConfiguredEnvironmentPath(filePath: string, workspaceRoot: string | undefined): string {
  if (!workspaceRoot) {
    return path.normalize(filePath);
  }

  const relative = path.relative(workspaceRoot, filePath);
  if (!relative.startsWith("..") && !path.isAbsolute(relative)) {
    return relative || DEFAULT_ENVIRONMENT_FILE;
  }
  return path.normalize(filePath);
}

export function parseEnvironmentFile(filePath: string): Record<string, string> {
  if (!fs.existsSync(filePath)) {
    return {};
  }

  const content = fs.readFileSync(filePath, "utf8");
  const entries: Record<string, string> = {};

  for (const rawLine of content.split(/\r?\n/)) {
    let line = rawLine.trim();
    if (!line || line.startsWith("#")) {
      continue;
    }

    if (line.startsWith("export ")) {
      line = line.slice("export ".length).trim();
    } else if (line.startsWith("set ")) {
      line = line.slice("set ".length).trim();
    }

    const separatorIndex = line.indexOf("=");
    if (separatorIndex <= 0) {
      continue;
    }

    const key = line.slice(0, separatorIndex).trim();
    let value = line.slice(separatorIndex + 1).trim();
    if (!key) {
      continue;
    }

    if (
      (value.startsWith('"') && value.endsWith('"')) ||
      (value.startsWith("'") && value.endsWith("'"))
    ) {
      value = value.slice(1, -1);
    }

    entries[key] = value;
  }

  return entries;
}

export function describeAvailability(
  source: string,
  availability: { secret: boolean; envFile: boolean; processEnv: boolean },
): string {
  if (source === ENV_FILE_SOURCE) {
    if (availability.envFile) {
      return availability.secret ? "Active via env file; SecretStorage also populated" : "Active via env file";
    }
    return availability.secret || availability.processEnv ? "Missing in env file; available elsewhere" : "Missing";
  }

  if (source === PROCESS_ENV_SOURCE) {
    if (availability.processEnv) {
      return availability.secret ? "Active via process env; SecretStorage also populated" : "Active via process env";
    }
    return availability.secret || availability.envFile ? "Missing in process env; available elsewhere" : "Missing";
  }

  if (availability.secret) {
    return availability.envFile ? "Active via SecretStorage; env file also populated" : "Active via SecretStorage";
  }
  return availability.envFile || availability.processEnv ? "Missing in SecretStorage; available elsewhere" : "Missing";
}
