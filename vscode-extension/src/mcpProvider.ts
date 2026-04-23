import * as fs from "fs";
import * as os from "os";
import * as path from "path";
import * as vscode from "vscode";

export type AcademicFiguresRuntimeTarget = "server" | "directRun";

export type AcademicFiguresRuntimeSpec = {
  mode: "local" | "package";
  command: string;
  args: string[];
  cwd?: string;
  env: Record<string, string>;
};

export const GOOGLE_API_KEY_SECRET = "academicFiguresMcp.googleApiKey";
export const OPENROUTER_API_KEY_SECRET = "academicFiguresMcp.openRouterApiKey";
export const OPENAI_API_KEY_SECRET = "academicFiguresMcp.openAiApiKey";
export const SECRET_STORAGE_SOURCE = "secretStorage";
export const ENV_FILE_SOURCE = "envFile";
export const PROCESS_ENV_SOURCE = "processEnv";
export const DEFAULT_ENV_FILE = ".vscode/academic-figures.env";
const DEFAULT_OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1";
const DEFAULT_OPENROUTER_MODEL = "google/gemini-3.1-flash-image-preview";
const DEFAULT_GOOGLE_MODEL = "gemini-3.1-flash-image-preview";
const DEFAULT_OPENAI_MODEL = "gpt-image-2";
const DEFAULT_OPENAI_BASE_URL = "https://api.openai.com/v1";
const DEFAULT_OPENAI_VISION_MODEL = "gpt-5.4-mini";
const DEFAULT_OPENAI_IMAGE_SIZE = "auto";
const DEFAULT_OPENROUTER_TITLE = "Academic Figures MCP";
const DEFAULT_OLLAMA_BASE_URL = "http://localhost:11434/v1";
const DEFAULT_OLLAMA_MODEL = "llava:latest";
const BLOCKED_ENVIRONMENT_KEYS = new Set([
  "DYLD_INSERT_LIBRARIES",
  "LD_LIBRARY_PATH",
  "LD_PRELOAD",
  "PATH",
  "PYTHONEXECUTABLE",
  "PYTHONHOME",
  "PYTHONPATH",
  "PYTHONSTARTUP",
]);
const BLOCKED_ENVIRONMENT_PREFIXES = ["DYLD_"];

export class AcademicFiguresMcpProvider
  implements vscode.McpServerDefinitionProvider<vscode.McpStdioServerDefinition>
{
  private readonly changeEmitter = new vscode.EventEmitter<void>();

  public readonly onDidChangeMcpServerDefinitions = this.changeEmitter.event;

  public constructor(
    private readonly context: vscode.ExtensionContext,
    private readonly outputChannel: vscode.OutputChannel,
  ) {}

  public refresh(): void {
    this.changeEmitter.fire();
  }

  public dispose(): void {
    this.changeEmitter.dispose();
  }

  public async provideMcpServerDefinitions(): Promise<vscode.McpStdioServerDefinition[]> {
    let runtime: AcademicFiguresRuntimeSpec;
    try {
      runtime = await this.getRuntimeSpec("server");
    } catch (error) {
      const message = this.describeRuntimeResolutionError(error);
      this.log(message);
      void vscode.window.showErrorMessage(message);
      return [];
    }

    this.log(
      `Providing MCP server definition (${runtime.mode}) -> ${runtime.command} ${runtime.args.join(" ")}`,
    );

    return [
      {
        label: "Academic Figures MCP",
        command: runtime.command,
        args: runtime.args,
        cwd: runtime.cwd ? vscode.Uri.file(runtime.cwd) : undefined,
        env: runtime.env,
      },
    ];
  }

  public async getRuntimeSpec(target: AcademicFiguresRuntimeTarget): Promise<AcademicFiguresRuntimeSpec> {
    const launch = this.resolveLaunch(target);
    const env = await this.buildEnvironment(launch.cwd);
    if (target === "server") {
      env.MCP_TRANSPORT = "stdio";
    }
    return {
      ...launch,
      env,
    };
  }

  /**
   * Resolve server before starting (optional last-minute customization).
   */
  public resolveMcpServerDefinition(
    server: vscode.McpStdioServerDefinition,
    _token: vscode.CancellationToken,
  ): vscode.ProviderResult<vscode.McpStdioServerDefinition> {
    this.log(`Resolving server "${server.label}"`);
    return server;
  }

  private async buildEnvironment(safeWorkingDirectory: string | undefined): Promise<Record<string, string>> {
    const config = vscode.workspace.getConfiguration("academicFiguresMcp");
    const provider = config.get<string>("imageProvider", "google");
    const credentialSource = config.get<string>("credentialSource", SECRET_STORAGE_SOURCE);
    const workspaceRoot = this.getWorkspaceRoot();
    const artifactRoot = workspaceRoot
      ? path.join(workspaceRoot, config.get<string>("outputDir", ".academic-figures"), "outputs")
      : "";
    const environmentFile = config.get<string>("environmentFile", DEFAULT_ENV_FILE);
    const envFilePath = this.resolveEnvironmentFilePath(environmentFile, workspaceRoot);
    const env: Record<string, string> = this.readProcessEnvironment();

    if (credentialSource === ENV_FILE_SOURCE && envFilePath) {
      Object.assign(env, this.readEnvironmentFile(envFilePath));
    }

    const googleApiKey =
      credentialSource === SECRET_STORAGE_SOURCE
        ? (await this.context.secrets.get(GOOGLE_API_KEY_SECRET)) ?? env.GOOGLE_API_KEY
        : env.GOOGLE_API_KEY;
    const openRouterApiKey =
      credentialSource === SECRET_STORAGE_SOURCE
        ? (await this.context.secrets.get(OPENROUTER_API_KEY_SECRET)) ?? env.OPENROUTER_API_KEY
        : env.OPENROUTER_API_KEY;
    const openAiApiKey =
      credentialSource === SECRET_STORAGE_SOURCE
        ? (await this.context.secrets.get(OPENAI_API_KEY_SECRET)) ?? env.OPENAI_API_KEY
        : env.OPENAI_API_KEY;

    env.AFM_IMAGE_PROVIDER = provider;
    if (provider === "openrouter") {
      env.GEMINI_MODEL = config.get<string>("openRouterModel", DEFAULT_OPENROUTER_MODEL);
    } else if (provider === "openai") {
      env.OPENAI_IMAGE_MODEL = config.get<string>("openAiModel", DEFAULT_OPENAI_MODEL);
      env.OPENAI_BASE_URL = config.get<string>("openAiBaseUrl", DEFAULT_OPENAI_BASE_URL);
      env.OPENAI_VISION_MODEL = config.get<string>("openAiVisionModel", DEFAULT_OPENAI_VISION_MODEL);
      env.OPENAI_IMAGE_SIZE = config.get<string>("openAiImageSize", DEFAULT_OPENAI_IMAGE_SIZE);
    } else if (provider === "ollama") {
      env.GEMINI_MODEL = config.get<string>("ollamaModel", DEFAULT_OLLAMA_MODEL);
    } else {
      env.GEMINI_MODEL = config.get<string>("googleModel", DEFAULT_GOOGLE_MODEL);
    }

    if (googleApiKey) {
      env.GOOGLE_API_KEY = googleApiKey;
    }
    if (openRouterApiKey) {
      env.OPENROUTER_API_KEY = openRouterApiKey;
    }
    if (openAiApiKey) {
      env.OPENAI_API_KEY = openAiApiKey;
    }
    if (provider === "openrouter") {
      env.OPENROUTER_BASE_URL = config.get<string>("openRouterBaseUrl", DEFAULT_OPENROUTER_BASE_URL);

      const referer = config.get<string>("openRouterReferer", "").trim();
      const title = config.get<string>("openRouterTitle", DEFAULT_OPENROUTER_TITLE).trim();
      if (referer) {
        env.OPENROUTER_HTTP_REFERER = referer;
      }
      if (title) {
        env.OPENROUTER_APP_TITLE = title;
      }
    }

    const ollamaBaseUrl = config.get<string>("ollamaBaseUrl", DEFAULT_OLLAMA_BASE_URL).trim();
    const ollamaModel = config.get<string>("ollamaModel", DEFAULT_OLLAMA_MODEL).trim();
    if (ollamaBaseUrl) {
      env.OLLAMA_BASE_URL = ollamaBaseUrl;
    }
    if (ollamaModel) {
      env.OLLAMA_MODEL = ollamaModel;
    }
    if (artifactRoot) {
      env.AFM_OUTPUT_DIR = artifactRoot;
    }
    if (safeWorkingDirectory) {
      env.AFM_SAFE_CWD = safeWorkingDirectory;
      env.PWD = safeWorkingDirectory;
    }

    return env;
  }

  private resolveLaunch(target: AcademicFiguresRuntimeTarget): { mode: "local" | "package"; command: string; args: string[]; cwd?: string } {
    const config = vscode.workspace.getConfiguration("academicFiguresMcp");
    const preferLocalSource = config.get<boolean>("preferLocalSource", true);
    const pythonCommand = config.get<string>("pythonCommand", "python");
    const packageName = config.get<string>("packageName", "academic-figures-mcp");
    const localRoot = preferLocalSource ? this.findLocalSource() : undefined;

    if (localRoot) {
      return {
        mode: "local",
        command: "uv",
        args:
          target === "server"
            ? ["run", pythonCommand, "-m", "src.server"]
            : ["run", pythonCommand, "-m", "src.direct_run"],
        cwd: this.resolveSafeWorkingDirectory(localRoot),
      };
    }

    return {
      mode: "package",
      command: "uvx",
      args: ["--from", packageName, target === "server" ? "afm-server" : "afm-run"],
      cwd: this.resolveSafeWorkingDirectory(this.getWorkspaceRoot()),
    };
  }

  private findLocalSource(): string | undefined {
    const workspaceRoot = this.getWorkspaceRoot();
    if (!workspaceRoot) {
      return undefined;
    }

    const pyprojectPath = path.join(workspaceRoot, "pyproject.toml");
    const requiredPaths = [
      pyprojectPath,
      path.join(workspaceRoot, "src", "server.py"),
      path.join(workspaceRoot, "src", "direct_run.py"),
      path.join(workspaceRoot, "src", "bootstrap.py"),
    ];
    if (!requiredPaths.every((candidate) => fs.existsSync(candidate))) {
      return undefined;
    }

    try {
      const pyproject = fs.readFileSync(pyprojectPath, "utf8");
      if (pyproject.includes('name = "academic-figures-mcp"')) {
        return workspaceRoot;
      }
    } catch {
      this.log("Failed to inspect pyproject.toml while resolving local source.");
    }

    return undefined;
  }

  private getWorkspaceRoot(): string | undefined {
    return vscode.workspace.workspaceFolders?.[0]?.uri.fsPath;
  }

  private resolveSafeWorkingDirectory(preferred: string | undefined): string {
    const candidates = [
      preferred,
      this.getWorkspaceRoot(),
      this.context.globalStorageUri.fsPath,
      os.homedir(),
      os.tmpdir(),
    ];

    for (const candidate of candidates) {
      if (!candidate || !this.isAccessibleDirectory(candidate)) {
        continue;
      }
      return candidate;
    }

    throw new Error("Academic Figures MCP could not resolve a safe working directory.");
  }

  private isAccessibleDirectory(candidate: string): boolean {
    try {
      return fs.statSync(candidate).isDirectory() && fs.accessSync(candidate, fs.constants.R_OK | fs.constants.X_OK) === undefined;
    } catch {
      return false;
    }
  }

  private readProcessEnvironment(): Record<string, string> {
    return {
      ...Object.fromEntries(
        Object.entries(process.env).filter((entry): entry is [string, string] => typeof entry[1] === "string"),
      ),
    };
  }

  private resolveEnvironmentFilePath(configuredPath: string, workspaceRoot: string | undefined): string | undefined {
    const trimmed = configuredPath.trim();
    if (!trimmed) {
      return undefined;
    }
    if (path.isAbsolute(trimmed)) {
      return trimmed;
    }
    if (workspaceRoot) {
      return path.join(workspaceRoot, trimmed);
    }
    return path.resolve(trimmed);
  }

  private readEnvironmentFile(filePath: string): Record<string, string> {
    if (!fs.existsSync(filePath)) {
      this.log(`Configured environment file was not found: ${filePath}`);
      return {};
    }

    try {
      const content = fs.readFileSync(filePath, "utf8");
      const values: Record<string, string> = {};

      for (const rawLine of content.split(/\r?\n/u)) {
        const trimmed = rawLine.trim();
        if (!trimmed || trimmed.startsWith("#")) {
          continue;
        }

        const normalized = trimmed.startsWith("export ")
          ? trimmed.slice("export ".length).trim()
          : trimmed.startsWith("set ")
            ? trimmed.slice("set ".length).trim()
            : trimmed;
        const separatorIndex = normalized.indexOf("=");
        if (separatorIndex <= 0) {
          continue;
        }

        const key = normalized.slice(0, separatorIndex).trim();
        const value = this.normalizeEnvironmentValue(normalized.slice(separatorIndex + 1).trim());
        if (key) {
          if (this.isBlockedEnvironmentKey(key)) {
            this.log(`Ignored blocked environment variable from ${filePath}: ${key}`);
            continue;
          }
          values[key] = value;
        }
      }

      this.log(`Loaded environment variables from ${filePath}`);
      return values;
    } catch {
      this.log(`Failed to read environment file: ${filePath}`);
      return {};
    }
  }

  private normalizeEnvironmentValue(value: string): string {
    if (
      (value.startsWith('"') && value.endsWith('"')) ||
      (value.startsWith("'") && value.endsWith("'"))
    ) {
      return value.slice(1, -1);
    }
    return value;
  }

  private isBlockedEnvironmentKey(key: string): boolean {
    const normalized = key.trim().toUpperCase();
    return (
      BLOCKED_ENVIRONMENT_KEYS.has(normalized) ||
      BLOCKED_ENVIRONMENT_PREFIXES.some((prefix) => normalized.startsWith(prefix))
    );
  }

  private describeRuntimeResolutionError(error: unknown): string {
    if (error instanceof Error && error.message.trim()) {
      return `Academic Figures MCP failed to resolve a launch runtime: ${error.message}`;
    }
    return "Academic Figures MCP failed to resolve a launch runtime.";
  }

  private log(message: string): void {
    this.outputChannel.appendLine(`[mcpProvider] ${message}`);
  }
}
