import { spawn } from "child_process";
import * as fs from "fs";
import * as path from "path";
import * as vscode from "vscode";

import {
  AcademicFiguresMcpProvider,
  type AcademicFiguresRuntimeSpec,
  GOOGLE_API_KEY_SECRET,
  OPENAI_API_KEY_SECRET,
  OPENROUTER_API_KEY_SECRET,
} from "./mcpProvider";
import {
  DEFAULT_ENVIRONMENT_FILE,
  DEFAULT_GOOGLE_MODEL,
  DEFAULT_OLLAMA_BASE_URL,
  DEFAULT_OLLAMA_MODEL,
  DEFAULT_OPENAI_BASE_URL,
  DEFAULT_OPENAI_IMAGE_SIZE,
  DEFAULT_OPENAI_MODEL,
  DEFAULT_OPENAI_VISION_MODEL,
  DEFAULT_OPENROUTER_BASE_URL,
  DEFAULT_OPENROUTER_MODEL,
  DEFAULT_OPENROUTER_REFERER,
  DEFAULT_OPENROUTER_TITLE,
  ENV_FILE_SOURCE,
  GOOGLE_PROVIDER,
  OLLAMA_PROVIDER,
  OPENAI_PROVIDER,
  OPENROUTER_PROVIDER,
  PROCESS_ENV_SOURCE,
  SECRET_STORAGE_SOURCE,
  describeAvailability,
  getApiKeyEnvName,
  getSupportedImageProvider,
  parseEnvironmentFile,
  resolveEnvironmentFilePath,
  toConfiguredEnvironmentPath,
} from "./connectionConfig";

type PresetGroup = {
  id: string;
  label: string;
  items: readonly string[];
};

type ResourceItem = {
  label: string;
  workspaceRelativePath: string;
  bundledRelativePath: string;
};

type ResourceGroup = {
  id: string;
  label: string;
  items: readonly ResourceItem[];
};

type CommandDeps = {
  artifactRoot: string;
  extensionUri: vscode.Uri;
  jobsProvider: JobsProvider;
  mcpProvider: AcademicFiguresMcpProvider;
  presetsProvider: PresetsProvider;
  resourcesProvider: ResourcesProvider;
  workspaceRoot: string | undefined;
};

type ConnectionActionId =
  | "googleSecret"
  | "openrouterSecret"
  | "openaiSecret"
  | "envFile"
  | "processEnv"
  | "openrouterSettings"
  | "openaiSettings"
  | "ollamaSettings"
  | "envTemplate";

type ConnectionAction = vscode.QuickPickItem & { id: ConnectionActionId };
type EnvironmentTemplateKind = "google" | "openrouter" | "openai" | "ollama";
type DirectRunCommand = "plan" | "generate" | "evaluate" | "transform";
type DirectRunResult = Record<string, unknown>;

const ARTIFACT_DIRS = ["jobs", "outputs", "prompts", "evaluations"] as const;
const FIRST_RUN_KEY = "academicFiguresMcp.firstRunShown";

const PRESET_GROUPS: readonly PresetGroup[] = [
  {
    id: "journal",
    label: "Journal Presets",
    items: ["Nature Multi-Panel", "Lancet Clinical Figure", "Generic Review Infographic"],
  },
  {
    id: "visual",
    label: "Visual Style Presets",
    items: ["Netter-like Anatomy", "Flat Medical Infographic", "Clean White Paper Schematic"],
  },
  {
    id: "domain",
    label: "Domain Presets",
    items: ["Drug Mechanism", "Airway Anatomy", "Clinical Workflow", "PK/PD Chart"],
  },
  {
    id: "routes",
    label: "Rendering Routes",
    items: [
      "image_generation",
      "image_edit",
      "code_render_matplotlib",
      "code_render_d2",
      "code_render_mermaid",
      "code_render_svg",
      "layout_assemble_svg",
    ],
  },
];

const RESOURCE_GROUPS: readonly ResourceGroup[] = [
  {
    id: "templates",
    label: "Prompt Templates",
    items: [
      {
        label: "Prompt Templates",
        workspaceRelativePath: "templates/prompt-templates.md",
        bundledRelativePath: "resources/knowledge/prompt-templates.md",
      },
    ],
  },
  {
    id: "standards",
    label: "Standards",
    items: [
      {
        label: "Anatomy Color Standards",
        workspaceRelativePath: "templates/anatomy-color-standards.md",
        bundledRelativePath: "resources/knowledge/anatomy-color-standards.md",
      },
      {
        label: "Journal Figure Standards",
        workspaceRelativePath: "templates/journal-figure-standards.md",
        bundledRelativePath: "resources/knowledge/journal-figure-standards.md",
      },
    ],
  },
  {
    id: "guides",
    label: "Rendering Guides",
    items: [
      {
        label: "Gemini Tips",
        workspaceRelativePath: "templates/gemini-tips.md",
        bundledRelativePath: "resources/knowledge/gemini-tips.md",
      },
      {
        label: "Code Rendering",
        workspaceRelativePath: "templates/code-rendering.md",
        bundledRelativePath: "resources/knowledge/code-rendering.md",
      },
      {
        label: "Scientific Figures Guide",
        workspaceRelativePath: "templates/scientific-figures-guide.md",
        bundledRelativePath: "resources/knowledge/scientific-figures-guide.md",
      },
    ],
  },
  {
    id: "evaluation",
    label: "Evaluation Rubrics",
    items: [
      {
        label: "AI Medical Illustration Evaluation",
        workspaceRelativePath: "templates/ai-medical-illustration-evaluation.md",
        bundledRelativePath: "resources/knowledge/ai-medical-illustration-evaluation.md",
      },
    ],
  },
];

let outputChannel: vscode.OutputChannel;

class CategoryItem extends vscode.TreeItem {
  public constructor(label: string) {
    super(label, vscode.TreeItemCollapsibleState.Expanded);
    this.contextValue = "category";
  }
}

class LeafItem extends vscode.TreeItem {
  public constructor(label: string, command?: vscode.Command, resourceUri?: vscode.Uri) {
    super(label, vscode.TreeItemCollapsibleState.None);
    this.command = command;
    this.resourceUri = resourceUri;
  }
}

class PresetsProvider implements vscode.TreeDataProvider<vscode.TreeItem> {
  private readonly emitter = new vscode.EventEmitter<void>();

  public readonly onDidChangeTreeData = this.emitter.event;

  public refresh(): void {
    this.emitter.fire();
  }

  public getTreeItem(element: vscode.TreeItem): vscode.TreeItem {
    return element;
  }

  public getChildren(element?: vscode.TreeItem): vscode.TreeItem[] {
    if (!element) {
      return PRESET_GROUPS.map((group) => new CategoryItem(group.label));
    }

    const group = PRESET_GROUPS.find((entry) => entry.label === element.label);
    if (!group) {
      return [];
    }
    return group.items.map(
      (item) =>
        new LeafItem(item, {
          command: "academicFiguresMcp.copyTextToClipboard",
          title: "Copy preset",
          arguments: [item],
        }),
    );
  }
}

class ResourcesProvider implements vscode.TreeDataProvider<vscode.TreeItem> {
  private readonly emitter = new vscode.EventEmitter<void>();

  public readonly onDidChangeTreeData = this.emitter.event;

  public constructor(
    private readonly workspaceRoot: string | undefined,
    private readonly extensionUri: vscode.Uri,
  ) {}

  public refresh(): void {
    this.emitter.fire();
  }

  public getTreeItem(element: vscode.TreeItem): vscode.TreeItem {
    return element;
  }

  public getChildren(element?: vscode.TreeItem): vscode.TreeItem[] {
    if (!element) {
      return RESOURCE_GROUPS.map((group) => new CategoryItem(group.label));
    }

    const group = RESOURCE_GROUPS.find((entry) => entry.label === element.label);
    if (!group) {
      return [];
    }
    return group.items.map((item) => {
      const resourceUri = resolveResourceUri(this.workspaceRoot, this.extensionUri, item);
      return new LeafItem(
        item.label,
        {
          command: "academicFiguresMcp.openWorkspaceFile",
          title: "Open resource",
          arguments: [resourceUri],
        },
        resourceUri,
      );
    });
  }
}

class JobsProvider implements vscode.TreeDataProvider<vscode.TreeItem> {
  private readonly emitter = new vscode.EventEmitter<void>();

  public readonly onDidChangeTreeData = this.emitter.event;

  public constructor(private readonly artifactRoot: string) {}

  public refresh(): void {
    this.emitter.fire();
  }

  public getTreeItem(element: vscode.TreeItem): vscode.TreeItem {
    return element;
  }

  public getChildren(element?: vscode.TreeItem): vscode.TreeItem[] {
    if (!element) {
      return ARTIFACT_DIRS.map((dirName) => new CategoryItem(dirName));
    }

    const folder = path.join(this.artifactRoot, String(element.label));
    if (!fs.existsSync(folder)) {
      return [];
    }

    return fs
      .readdirSync(folder, { withFileTypes: true })
      .sort((left, right) => right.name.localeCompare(left.name))
      .slice(0, 20)
      .map((entry) => {
        const filePath = path.join(folder, entry.name);
        return new LeafItem(
          entry.name,
          {
            command: "vscode.open",
            title: "Open artifact",
            arguments: [vscode.Uri.file(filePath)],
          },
          vscode.Uri.file(filePath),
        );
      });
  }
}

export async function activate(context: vscode.ExtensionContext): Promise<void> {
  outputChannel = vscode.window.createOutputChannel("Academic Figures MCP");
  context.subscriptions.push(outputChannel);
  log("Activating extension.");

  await updateApiKeyContext(context);

  const workspaceRoot = getWorkspaceRoot();
  const artifactRoot = ensureArtifactDirectories(workspaceRoot);
  const presetsProvider = new PresetsProvider();
  const resourcesProvider = new ResourcesProvider(workspaceRoot, context.extensionUri);
  const jobsProvider = new JobsProvider(artifactRoot);
  const mcpProvider = new AcademicFiguresMcpProvider(context, outputChannel);
  context.subscriptions.push({ dispose: () => mcpProvider.dispose() });

  context.subscriptions.push(
    vscode.window.registerTreeDataProvider("academicFigures.presets", presetsProvider),
    vscode.window.registerTreeDataProvider("academicFigures.resources", resourcesProvider),
    vscode.window.registerTreeDataProvider("academicFigures.jobs", jobsProvider),
  );

  if (typeof vscode.lm?.registerMcpServerDefinitionProvider === "function") {
    context.subscriptions.push(
      vscode.lm.registerMcpServerDefinitionProvider("academic-figures-mcp.servers", mcpProvider),
    );
    log("Registered MCP server definition provider.");
  } else {
    log("MCP server definition provider API is unavailable in this VS Code build.");
  }

  // Status bar item (like zotero-keeper)
  const statusBarItem = vscode.window.createStatusBarItem(vscode.StatusBarAlignment.Right, 100);
  statusBarItem.text = "$(paintcan) AFM";
  statusBarItem.tooltip = "Academic Figures MCP Quick Menu";
  statusBarItem.command = "academicFiguresMcp.showQuickMenu";
  statusBarItem.show();
  context.subscriptions.push(statusBarItem);

  await maybeShowWalkthrough(context);

  registerCommands(context, {
    artifactRoot,
    extensionUri: context.extensionUri,
    jobsProvider,
    mcpProvider,
    presetsProvider,
    resourcesProvider,
    workspaceRoot,
  });
}

export function deactivate(): void {
  log("Deactivating extension.");
}

function registerCommands(
  context: vscode.ExtensionContext,
  deps: CommandDeps,
): void {
  const register = (command: string, callback: (...args: unknown[]) => unknown): void => {
    context.subscriptions.push(vscode.commands.registerCommand(command, callback));
  };

  register("academicFiguresMcp.copyTextToClipboard", async (value: unknown) => {
    const text = String(value ?? "");
    await vscode.env.clipboard.writeText(text);
    vscode.window.showInformationMessage(`Copied: ${text}`);
  });

  register("academicFiguresMcp.openWorkspaceFile", async (filePath: unknown) => {
    const target = toResourceUri(filePath);
    if (!target) {
      vscode.window.showWarningMessage("Requested resource file could not be resolved.");
      return;
    }
    if (target.scheme === "file" && !fs.existsSync(target.fsPath)) {
      vscode.window.showWarningMessage("Requested resource file was not found.");
      return;
    }
    const document = await vscode.workspace.openTextDocument(target);
    await vscode.window.showTextDocument(document, { preview: false });
  });

  register("academicFiguresMcp.configureApiKey", async () => {
    await showConnectionMenu(context, deps);
  });

  register("academicFiguresMcp.createEnvironmentFile", async () => {
    await createEnvironmentFileTemplate(context, deps);
  });

  register("academicFiguresMcp.insertMcpSettings", async () => {
    if (!deps.workspaceRoot) {
      vscode.window.showErrorMessage("Open a workspace folder before inserting MCP settings.");
      return;
    }

    const vscodeDir = path.join(deps.workspaceRoot, ".vscode");
    const settingsPath = path.join(vscodeDir, "mcp.json");
    fs.mkdirSync(vscodeDir, { recursive: true });

    const current = readJsonFile(settingsPath);
    const currentServers = toObjectRecord(current.servers) ?? {};
    const mergedServer = {
      ...(toObjectRecord(currentServers.academicFigures) ?? {}),
      ...(toObjectRecord(currentServers["academic-figures"]) ?? {}),
    };
    const nextServers = { ...currentServers };
    delete nextServers.academicFigures;

    const next = {
      ...current,
      servers: {
        ...nextServers,
        "academic-figures": buildWorkspaceMcpServerDefinition(mergedServer),
      },
    };

    fs.writeFileSync(settingsPath, `${JSON.stringify(next, null, 2)}\n`, "utf8");
    const document = await vscode.workspace.openTextDocument(settingsPath);
    await vscode.window.showTextDocument(document, { preview: false });
    vscode.window.showInformationMessage(
      "Inserted a cross-platform .vscode/mcp.json with runtime environment placeholders. The extension provider can use SecretStorage, an env file, or process env.",
    );
  });

  register("academicFiguresMcp.planFigureFromPmid", async () => {
    await runPlanFigureCommand(deps);
  });

  register("academicFiguresMcp.generateFigure", async () => {
    await runGenerateFigureCommand(deps);
  });

  register("academicFiguresMcp.transformFigureStyle", async () => {
    const imagePath = await vscode.window.showInputBox({
      prompt: "Existing image path",
      placeHolder: ".academic-figures/outputs/example.png",
    });
    if (!imagePath) {
      return;
    }
    const preset = await vscode.window.showQuickPick(
      PRESET_GROUPS.flatMap((group) => group.items),
      { placeHolder: "Target style preset" },
    );
    if (!preset) {
      return;
    }
    await runTransformFigureCommand(
      deps,
      imagePath,
      `Transform this academic figure to the "${preset}" preset while preserving scientific meaning, label readability, and citations.`,
    );
  });

  register("academicFiguresMcp.evaluateFigure", async () => {
    await runEvaluateFigureCommand(deps);
  });

  register("academicFiguresMcp.browsePresets", async () => {
    await vscode.commands.executeCommand("workbench.view.extension.academicFigures");
    vscode.window.showInformationMessage("Open the Presets view in the Academic Figures activity bar.");
  });

  register("academicFiguresMcp.browseKnowledgeAssets", async () => {
    const choices = RESOURCE_GROUPS.flatMap((group) =>
      group.items.map((item) => ({
        label: item.label,
        description: item.workspaceRelativePath,
      })),
    );
    const selected = await vscode.window.showQuickPick(choices, { placeHolder: "Open a knowledge asset" });
    if (!selected) {
      return;
    }

    const item = RESOURCE_GROUPS.flatMap((group) => group.items).find(
      (resource) => resource.label === selected.label,
    );
    if (!item) {
      return;
    }

    const resourceUri = resolveResourceUri(deps.workspaceRoot, deps.extensionUri, item);
    await vscode.commands.executeCommand("academicFiguresMcp.openWorkspaceFile", resourceUri);
  });

  register("academicFiguresMcp.openRecentJobs", async () => {
    const uri = vscode.Uri.file(deps.artifactRoot);
    await vscode.env.openExternal(uri);
  });

  register("academicFiguresMcp.refreshViews", async () => {
    deps.jobsProvider.refresh();
    deps.presetsProvider.refresh();
    deps.resourcesProvider.refresh();
    deps.mcpProvider.refresh();
    vscode.window.showInformationMessage("Academic Figures views refreshed.");
  });

  register("academicFiguresMcp.showStatus", async () => {
    const panel = vscode.window.createWebviewPanel(
      "academicFiguresStatus",
      "Academic Figures MCP Status",
      vscode.ViewColumn.One,
      { enableScripts: false },
    );
    panel.webview.html = await buildStatusHtml(context, deps.workspaceRoot, deps.artifactRoot);
  });

  register("academicFiguresMcp.showOutput", () => {
    outputChannel.show();
  });

  register("academicFiguresMcp.showQuickMenu", async () => {
    const items: vscode.QuickPickItem[] = [
      { label: "$(wand) Setup Wizard", description: "One-click setup" },
      { label: "$(paintcan) Generate Figure", description: "From PMID" },
      { label: "$(edit) Transform Style", description: "Restyle existing image" },
      { label: "$(checklist) Evaluate Figure", description: "8-domain rubric" },
      { label: "$(plug) Configure Connection", description: "Key, env file, OpenRouter, Ollama" },
      { label: "$(file-code) Create Env File", description: "Generate an env template" },
      { label: "$(gear) Insert MCP Settings", description: ".vscode/mcp.json" },
      { label: "$(sync) Reinstall Python Env", description: "Run uv sync --all-extras" },
      { label: "$(info) Show Status", description: "Extension status" },
      { label: "$(output) Show Output", description: "Output channel" },
    ];
    const picked = await vscode.window.showQuickPick(items, { placeHolder: "Academic Figures MCP" });
    if (!picked) {
      return;
    }
    const commandMap: Record<string, string> = {
      "$(wand) Setup Wizard": "academicFiguresMcp.setupWizard",
      "$(paintcan) Generate Figure": "academicFiguresMcp.generateFigure",
      "$(edit) Transform Style": "academicFiguresMcp.transformFigureStyle",
      "$(checklist) Evaluate Figure": "academicFiguresMcp.evaluateFigure",
      "$(plug) Configure Connection": "academicFiguresMcp.configureApiKey",
      "$(file-code) Create Env File": "academicFiguresMcp.createEnvironmentFile",
      "$(gear) Insert MCP Settings": "academicFiguresMcp.insertMcpSettings",
      "$(sync) Reinstall Python Env": "academicFiguresMcp.reinstallPythonEnv",
      "$(info) Show Status": "academicFiguresMcp.showStatus",
      "$(output) Show Output": "academicFiguresMcp.showOutput",
    };
    const command = commandMap[picked.label];
    if (command) {
      await vscode.commands.executeCommand(command);
    }
  });

  register("academicFiguresMcp.setupWizard", async () => {
    const configured = await showConnectionMenu(
      context,
      deps,
      "Step 1/2: Choose how the extension should load provider credentials",
      true,
    );
    if (!configured) {
      return;
    }

    if (deps.workspaceRoot) {
      await vscode.commands.executeCommand("academicFiguresMcp.insertMcpSettings");
      log("Setup Wizard: MCP settings inserted.");
    }

    vscode.window.showInformationMessage(
      `Academic Figures MCP setup complete with provider ${getCurrentImageProvider()} and source ${getCredentialSourceLabel()}. Try asking Copilot to generate a figure.`,
    );
  });

  register("academicFiguresMcp.reinstallPythonEnv", async () => {
    if (!deps.workspaceRoot) {
      vscode.window.showErrorMessage("Open a workspace folder first.");
      return;
    }

    const terminal = vscode.window.createTerminal({
      name: "AFM Reinstall",
      cwd: deps.workspaceRoot,
    });
    terminal.show();
    terminal.sendText("uv sync --all-extras");
    vscode.window.showInformationMessage("Reinstalling Python environment via uv...");
  });
}

async function runPlanFigureCommand(deps: CommandDeps): Promise<void> {
  const pmid = await vscode.window.showInputBox({ prompt: "PMID", placeHolder: "41657234" });
  if (!pmid) {
    return;
  }

  const result = await runDirectTool(
    deps,
    "plan",
    ["--pmid", pmid, "--language", "zh-TW", "--output-size", "1024x1536"],
    "Planning academic figure",
  );
  if (!result) {
    return;
  }

  const artifactPath = writeJsonArtifact(
    deps.artifactRoot,
    "jobs",
    `plan_${slugify(pmid)}_${Date.now()}.json`,
    result,
  );
  deps.jobsProvider.refresh();
  await openTextArtifact(artifactPath);

  const figureType = String(result.selected_figure_type ?? "auto");
  const renderRoute = String(result.render_route ?? "unknown");
  vscode.window.showInformationMessage(`Plan ready: ${figureType} via ${renderRoute}.`);
}

async function runGenerateFigureCommand(deps: CommandDeps): Promise<void> {
  const pmid = await vscode.window.showInputBox({ prompt: "PMID", placeHolder: "41657234" });
  if (!pmid) {
    return;
  }

  const result = await runDirectTool(
    deps,
    "generate",
    ["--pmid", pmid, "--language", "zh-TW", "--output-size", "1024x1536"],
    "Generating academic figure",
  );
  if (!result) {
    return;
  }

  writeJsonArtifact(
    deps.artifactRoot,
    "jobs",
    `generate_${slugify(pmid)}_${Date.now()}.json`,
    result,
  );
  deps.jobsProvider.refresh();

  const outputPath = typeof result.output_path === "string" ? result.output_path : "";
  if (outputPath && fs.existsSync(outputPath)) {
    await openArtifact(outputPath);
    vscode.window.showInformationMessage(`Figure generated: ${path.basename(outputPath)}`);
    return;
  }

  vscode.window.showWarningMessage("Generation finished without an openable output artifact. Check the JSON job log.");
}

async function runEvaluateFigureCommand(deps: CommandDeps): Promise<void> {
  const imagePath = await vscode.window.showInputBox({
    prompt: "Image path to evaluate",
    placeHolder: ".academic-figures/outputs/example.png",
  });
  if (!imagePath) {
    return;
  }

  const result = await runDirectTool(
    deps,
    "evaluate",
    ["--image-path", imagePath, "--figure-type", "infographic"],
    "Evaluating academic figure",
  );
  if (!result) {
    return;
  }

  const artifactPath = writeJsonArtifact(
    deps.artifactRoot,
    "evaluations",
    `evaluation_${slugify(path.basename(imagePath))}_${Date.now()}.json`,
    result,
  );
  deps.jobsProvider.refresh();
  await openTextArtifact(artifactPath);
  vscode.window.showInformationMessage("Evaluation complete. Review the saved rubric report.");
}

async function runTransformFigureCommand(
  deps: CommandDeps,
  imagePath: string,
  feedback: string,
): Promise<void> {
  const result = await runDirectTool(
    deps,
    "transform",
    ["--image-path", imagePath, "--feedback", feedback],
    "Transforming academic figure",
  );
  if (!result) {
    return;
  }

  writeJsonArtifact(
    deps.artifactRoot,
    "jobs",
    `transform_${slugify(path.basename(imagePath))}_${Date.now()}.json`,
    result,
  );
  deps.jobsProvider.refresh();

  const outputPath = typeof result.output_path === "string" ? result.output_path : "";
  if (outputPath && fs.existsSync(outputPath)) {
    await openArtifact(outputPath);
    vscode.window.showInformationMessage(`Transformed figure saved: ${path.basename(outputPath)}`);
    return;
  }

  const artifactPath = writeJsonArtifact(
    deps.artifactRoot,
    "evaluations",
    `transform_error_${slugify(path.basename(imagePath))}_${Date.now()}.json`,
    result,
  );
  await openTextArtifact(artifactPath);
}

async function runDirectTool(
  deps: CommandDeps,
  command: DirectRunCommand,
  extraArgs: string[],
  progressTitle: string,
): Promise<DirectRunResult | undefined> {
  let runtime: AcademicFiguresRuntimeSpec;
  try {
    runtime = await deps.mcpProvider.getRuntimeSpec("directRun");
  } catch (error) {
    const message =
      error instanceof Error && error.message.trim()
        ? error.message
        : `Direct-run ${command} failed before launch.`;
    vscode.window.showErrorMessage(message);
    log(`[direct-run:${command}:launch-error] ${message}`);
    return undefined;
  }
  const args = [...runtime.args, command, ...extraArgs];
  log(`Direct-run ${command}: ${runtime.command} ${args.join(" ")}`);

  const outcome = await vscode.window.withProgress(
    {
      location: vscode.ProgressLocation.Notification,
      title: progressTitle,
    },
    async () => executeRuntime(runtime, args),
  );

  if (outcome.stderr.trim()) {
    log(`[direct-run:${command}:stderr] ${outcome.stderr.trim()}`);
  }
  if (!outcome.stdout.trim()) {
    vscode.window.showErrorMessage(`Direct-run ${command} returned no JSON output.`);
    return undefined;
  }

  try {
    const parsed = JSON.parse(outcome.stdout) as DirectRunResult;
    if (outcome.exitCode !== 0 && parsed.status !== "ok") {
      const message = typeof parsed.error === "string" ? parsed.error : `Direct-run ${command} failed.`;
      vscode.window.showErrorMessage(message);
    }
    return parsed;
  } catch {
    vscode.window.showErrorMessage(`Direct-run ${command} returned invalid JSON. Check the output channel.`);
    log(`[direct-run:${command}:stdout] ${outcome.stdout}`);
    return undefined;
  }
}

async function executeRuntime(
  runtime: AcademicFiguresRuntimeSpec,
  args: string[],
): Promise<{ stdout: string; stderr: string; exitCode: number | null }> {
  return new Promise((resolve, reject) => {
    const child = spawn(runtime.command, args, {
      cwd: runtime.cwd,
      env: { ...process.env, ...runtime.env },
      windowsHide: true,
    });

    let stdout = "";
    let stderr = "";
    child.stdout.on("data", (chunk: Buffer | string) => {
      stdout += chunk.toString();
    });
    child.stderr.on("data", (chunk: Buffer | string) => {
      stderr += chunk.toString();
    });
    child.on("error", (error) => {
      reject(error);
    });
    child.on("close", (exitCode) => {
      resolve({ stdout: stdout.trim(), stderr: stderr.trim(), exitCode });
    });
  });
}

function writeJsonArtifact(
  artifactRoot: string,
  category: typeof ARTIFACT_DIRS[number],
  fileName: string,
  data: unknown,
): string {
  const filePath = path.join(artifactRoot, category, fileName);
  fs.writeFileSync(filePath, `${JSON.stringify(data, null, 2)}\n`, "utf8");
  return filePath;
}

async function openArtifact(filePath: string): Promise<void> {
  await vscode.commands.executeCommand("vscode.open", vscode.Uri.file(filePath));
}

async function openTextArtifact(filePath: string): Promise<void> {
  const document = await vscode.workspace.openTextDocument(filePath);
  await vscode.window.showTextDocument(document, { preview: false });
}

function resolveResourceUri(
  workspaceRoot: string | undefined,
  extensionUri: vscode.Uri,
  item: ResourceItem,
): vscode.Uri {
  if (workspaceRoot) {
    const workspacePath = path.join(workspaceRoot, item.workspaceRelativePath);
    if (fs.existsSync(workspacePath)) {
      return vscode.Uri.file(workspacePath);
    }
  }

  return vscode.Uri.joinPath(extensionUri, item.bundledRelativePath);
}

function toResourceUri(value: unknown): vscode.Uri | undefined {
  if (value instanceof vscode.Uri) {
    return value;
  }
  if (typeof value === "string" && value) {
    return vscode.Uri.file(value);
  }
  if (value && typeof value === "object" && "scheme" in value && "path" in value) {
    return vscode.Uri.from(value as Parameters<typeof vscode.Uri.from>[0]);
  }
  return undefined;
}

function slugify(value: string): string {
  return value.replace(/[^a-z0-9]+/giu, "_").replace(/^_+|_+$/gu, "").toLowerCase() || "artifact";
}

async function buildStatusHtml(
  context: vscode.ExtensionContext,
  workspaceRoot: string | undefined,
  artifactRoot: string,
): Promise<string> {
  const config = vscode.workspace.getConfiguration("academicFiguresMcp");
  const currentProvider = getCurrentImageProvider();
  const credentialSource = getCredentialSource();
  const environmentFileSetting = config.get<string>("environmentFile", DEFAULT_ENVIRONMENT_FILE);
  const environmentFilePath = resolveEnvironmentFilePath(workspaceRoot, environmentFileSetting);
  const environmentValues = parseEnvironmentFile(environmentFilePath);
  const environmentFileExists = fs.existsSync(environmentFilePath);
  const googleSecretConfigured = Boolean(await context.secrets.get(GOOGLE_API_KEY_SECRET));
  const openRouterSecretConfigured = Boolean(await context.secrets.get(OPENROUTER_API_KEY_SECRET));
  const openAiSecretConfigured = Boolean(await context.secrets.get(OPENAI_API_KEY_SECRET));
  const googleProcessConfigured = Boolean(process.env.GOOGLE_API_KEY);
  const openRouterProcessConfigured = Boolean(process.env.OPENROUTER_API_KEY);
  const openAiProcessConfigured = Boolean(process.env.OPENAI_API_KEY);
  const localSource = Boolean(workspaceRoot && fs.existsSync(path.join(workspaceRoot, "src", "presentation", "server.py")));
  const unsafeEnvFile = Boolean(workspaceRoot && fs.existsSync(path.join(workspaceRoot, "env")));
  const activeModel =
    currentProvider === OPENROUTER_PROVIDER
      ? config.get<string>("openRouterModel", DEFAULT_OPENROUTER_MODEL)
      : currentProvider === OPENAI_PROVIDER
        ? config.get<string>("openAiModel", DEFAULT_OPENAI_MODEL)
      : currentProvider === OLLAMA_PROVIDER
        ? config.get<string>("ollamaModel", DEFAULT_OLLAMA_MODEL)
      : config.get<string>("googleModel", DEFAULT_GOOGLE_MODEL);

  const rows = [
    ["Workspace", workspaceRoot ?? "No workspace folder"],
    ["Artifact Root", artifactRoot],
    ["Transport", config.get<string>("transport", "stdio")],
    ["Image Provider", currentProvider],
    ["Credential Source", getCredentialSourceLabel(credentialSource)],
    ["Active Model", activeModel],
    ["Prefer Local Source", String(config.get<boolean>("preferLocalSource", true))],
    ["Local Source Found", String(localSource)],
    ["Environment File Setting", environmentFileSetting || DEFAULT_ENVIRONMENT_FILE],
    ["Environment File Path", environmentFilePath],
    ["Environment File Exists", environmentFileExists ? "Yes" : "No"],
    [
      "GOOGLE_API_KEY",
      describeAvailability(credentialSource, {
        secret: googleSecretConfigured,
        envFile: Boolean(environmentValues.GOOGLE_API_KEY),
        processEnv: googleProcessConfigured,
      }),
    ],
    [
      "OPENROUTER_API_KEY",
      describeAvailability(credentialSource, {
        secret: openRouterSecretConfigured,
        envFile: Boolean(environmentValues.OPENROUTER_API_KEY),
        processEnv: openRouterProcessConfigured,
      }),
    ],
    [
      "OPENAI_API_KEY",
      describeAvailability(credentialSource, {
        secret: openAiSecretConfigured,
        envFile: Boolean(environmentValues.OPENAI_API_KEY),
        processEnv: openAiProcessConfigured,
      }),
    ],
    [
      "OpenRouter Base URL",
      config.get<string>("openRouterBaseUrl", DEFAULT_OPENROUTER_BASE_URL),
    ],
    ["OpenAI Base URL", config.get<string>("openAiBaseUrl", DEFAULT_OPENAI_BASE_URL)],
    ["OpenAI Vision Model", config.get<string>("openAiVisionModel", DEFAULT_OPENAI_VISION_MODEL)],
    ["Ollama Base URL", config.get<string>("ollamaBaseUrl", DEFAULT_OLLAMA_BASE_URL)],
    ["Ollama Model", config.get<string>("ollamaModel", DEFAULT_OLLAMA_MODEL)],
    ["Plaintext env file", unsafeEnvFile ? "Warning: env file detected in repo root" : "Not detected"],
  ];

  const body = rows
    .map(
      ([label, value]) =>
        `<tr><td><strong>${escapeHtml(label)}</strong></td><td>${escapeHtml(value)}</td></tr>`,
    )
    .join("");

  return `<!DOCTYPE html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>Academic Figures MCP Status</title>
    <style>
      body { font-family: var(--vscode-font-family); padding: 20px; color: var(--vscode-foreground); background: var(--vscode-editor-background); }
      table { width: 100%; border-collapse: collapse; }
      td { padding: 10px; border-bottom: 1px solid var(--vscode-panel-border); vertical-align: top; }
      h1 { margin-top: 0; }
      .note { margin-top: 16px; padding: 12px; border-radius: 8px; background: var(--vscode-textCodeBlock-background); }
    </style>
  </head>
  <body>
    <h1>Academic Figures MCP Status</h1>
    <table>${body}</table>
    <div class="note">
      Runtime execution now supports Google Gemini, OpenRouter, and a local Ollama SVG brief route. Ollama can also perform vision-based evaluation, but bitmap image editing still needs Google or OpenRouter.
    </div>
  </body>
</html>`;
}

function ensureArtifactDirectories(workspaceRoot: string | undefined): string {
  const configured = vscode.workspace.getConfiguration("academicFiguresMcp").get<string>("outputDir", ".academic-figures");
  const root = workspaceRoot ? path.join(workspaceRoot, configured) : path.join(process.cwd(), configured);
  fs.mkdirSync(root, { recursive: true });
  for (const name of ARTIFACT_DIRS) {
    fs.mkdirSync(path.join(root, name), { recursive: true });
  }
  return root;
}

function getWorkspaceRoot(): string | undefined {
  return vscode.workspace.workspaceFolders?.[0]?.uri.fsPath;
}

function readJsonFile(filePath: string): Record<string, unknown> {
  if (!fs.existsSync(filePath)) {
    return {};
  }

  try {
    return JSON.parse(fs.readFileSync(filePath, "utf8")) as Record<string, unknown>;
  } catch {
    return {};
  }
}

function toObjectRecord(value: unknown): Record<string, unknown> | undefined {
  return typeof value === "object" && value ? (value as Record<string, unknown>) : undefined;
}

function buildWorkspaceMcpServerDefinition(
  existing: Record<string, unknown>,
): Record<string, unknown> {
  const server: Record<string, unknown> = {
    type: "stdio",
    command: "uv",
    args: ["run", "--project", "${workspaceFolder}", "python", "-m", "src.server"],
  };

  if (typeof existing.envFile === "string" && existing.envFile.trim()) {
    server.envFile = existing.envFile;
  }

  const existingEnv = toObjectRecord(existing.env);
  if (existingEnv) {
    server.env = existingEnv;
  }

  return server;
}

function escapeHtml(value: string): string {
  return value
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}

function log(message: string): void {
  outputChannel?.appendLine(message);
}

async function updateApiKeyContext(context: vscode.ExtensionContext): Promise<void> {
  const credentialSource = getCredentialSource();
  const environmentValues =
    credentialSource === ENV_FILE_SOURCE
      ? parseEnvironmentFile(resolveEnvironmentFilePath(getWorkspaceRoot(), getEnvironmentFileSetting()))
      : {};
  const googleConfigured =
    credentialSource === SECRET_STORAGE_SOURCE
      ? Boolean(await context.secrets.get(GOOGLE_API_KEY_SECRET))
      : credentialSource === ENV_FILE_SOURCE
        ? Boolean(environmentValues.GOOGLE_API_KEY)
        : Boolean(process.env.GOOGLE_API_KEY);
  const openRouterConfigured =
    credentialSource === SECRET_STORAGE_SOURCE
      ? Boolean(await context.secrets.get(OPENROUTER_API_KEY_SECRET))
      : credentialSource === ENV_FILE_SOURCE
        ? Boolean(environmentValues.OPENROUTER_API_KEY)
        : Boolean(process.env.OPENROUTER_API_KEY);
  const openAiConfigured =
    credentialSource === SECRET_STORAGE_SOURCE
      ? Boolean(await context.secrets.get(OPENAI_API_KEY_SECRET))
      : credentialSource === ENV_FILE_SOURCE
        ? Boolean(environmentValues.OPENAI_API_KEY)
        : Boolean(process.env.OPENAI_API_KEY);
  const config = vscode.workspace.getConfiguration("academicFiguresMcp");
  const ollamaConfigured =
    credentialSource === ENV_FILE_SOURCE
      ? Boolean(environmentValues.OLLAMA_BASE_URL || config.get<string>("ollamaBaseUrl"))
        && Boolean(environmentValues.OLLAMA_MODEL || config.get<string>("ollamaModel"))
      : credentialSource === PROCESS_ENV_SOURCE
        ? Boolean(process.env.OLLAMA_BASE_URL || config.get<string>("ollamaBaseUrl"))
          && Boolean(process.env.OLLAMA_MODEL || config.get<string>("ollamaModel"))
        : Boolean(config.get<string>("ollamaBaseUrl")) && Boolean(config.get<string>("ollamaModel"));
  const activeConfigured =
    getCurrentImageProvider() === OPENROUTER_PROVIDER
      ? openRouterConfigured
      : getCurrentImageProvider() === OPENAI_PROVIDER
        ? openAiConfigured
      : getCurrentImageProvider() === OLLAMA_PROVIDER
        ? ollamaConfigured
        : googleConfigured;

  await vscode.commands.executeCommand("setContext", "academicFiguresMcp.googleApiKeyConfigured", googleConfigured);
  await vscode.commands.executeCommand(
    "setContext",
    "academicFiguresMcp.openRouterApiKeyConfigured",
    openRouterConfigured,
  );
  await vscode.commands.executeCommand(
    "setContext",
    "academicFiguresMcp.openAiApiKeyConfigured",
    openAiConfigured,
  );
  await vscode.commands.executeCommand(
    "setContext",
    "academicFiguresMcp.anyApiKeyConfigured",
    activeConfigured,
  );
}

async function maybeShowWalkthrough(context: vscode.ExtensionContext): Promise<void> {
  const firstRunShown = context.globalState.get<boolean>(FIRST_RUN_KEY, false);
  if (firstRunShown) {
    return;
  }

  await context.globalState.update(FIRST_RUN_KEY, true);
  await vscode.commands.executeCommand(
    "workbench.action.openWalkthrough",
    "u9401066.academic-figures-mcp#academicFigures.getStarted",
    false,
  );
}

function getCurrentImageProvider(): string {
  return vscode.workspace.getConfiguration("academicFiguresMcp").get<string>("imageProvider", GOOGLE_PROVIDER);
}

function getSecretNameForProvider(provider: string): string {
  if (provider === OPENROUTER_PROVIDER) {
    return OPENROUTER_API_KEY_SECRET;
  }
  if (provider === OPENAI_PROVIDER) {
    return OPENAI_API_KEY_SECRET;
  }
  return GOOGLE_API_KEY_SECRET;
}

function getApiKeyLabel(provider: string): string {
  return getApiKeyEnvName(provider);
}

function getCredentialSource(): string {
  return vscode.workspace
    .getConfiguration("academicFiguresMcp")
    .get<string>("credentialSource", SECRET_STORAGE_SOURCE);
}

function getCredentialSourceLabel(source = getCredentialSource()): string {
  if (source === ENV_FILE_SOURCE) {
    return "Environment file";
  }
  if (source === PROCESS_ENV_SOURCE) {
    return "Process environment";
  }
  return "VS Code SecretStorage";
}

function getEnvironmentFileSetting(): string {
  return vscode.workspace
    .getConfiguration("academicFiguresMcp")
    .get<string>("environmentFile", DEFAULT_ENVIRONMENT_FILE);
}

function getConfigurationTarget(): vscode.ConfigurationTarget {
  return vscode.workspace.workspaceFolders ? vscode.ConfigurationTarget.Workspace : vscode.ConfigurationTarget.Global;
}

async function updateCredentialSourceSetting(source: string): Promise<void> {
  await vscode.workspace
    .getConfiguration("academicFiguresMcp")
    .update("credentialSource", source, getConfigurationTarget());
}

async function updateEnvironmentFileSetting(configuredPath: string): Promise<void> {
  await vscode.workspace
    .getConfiguration("academicFiguresMcp")
    .update("environmentFile", configuredPath, getConfigurationTarget());
}

async function updateImageProviderSetting(provider: string): Promise<void> {
  await vscode.workspace
    .getConfiguration("academicFiguresMcp")
    .update("imageProvider", getSupportedImageProvider(provider), getConfigurationTarget());
}

async function pickImageProvider(
  placeHolder?: string,
): Promise<
  | typeof GOOGLE_PROVIDER
  | typeof OPENROUTER_PROVIDER
  | typeof OPENAI_PROVIDER
  | typeof OLLAMA_PROVIDER
  | undefined
> {
  const currentProvider = getCurrentImageProvider();
  const picked = await vscode.window.showQuickPick(
    [
      {
        label: GOOGLE_PROVIDER,
        description: "Direct Google Gemini API",
        detail: `Use GOOGLE_API_KEY with ${DEFAULT_GOOGLE_MODEL}`,
      },
      {
        label: OPENROUTER_PROVIDER,
        description: "OpenRouter",
        detail: `Use OPENROUTER_API_KEY with ${DEFAULT_OPENROUTER_MODEL}`,
      },
      {
        label: OPENAI_PROVIDER,
        description: "OpenAI Images API",
        detail: `Use OPENAI_API_KEY with ${DEFAULT_OPENAI_MODEL}`,
      },
      {
        label: OLLAMA_PROVIDER,
        description: "Local Ollama runtime",
        detail: `Use ${DEFAULT_OLLAMA_MODEL} at ${DEFAULT_OLLAMA_BASE_URL}`,
      },
    ],
    {
      placeHolder: placeHolder ?? `Choose image provider (current: ${currentProvider})`,
    },
  );
  return picked?.label as
    | typeof GOOGLE_PROVIDER
    | typeof OPENROUTER_PROVIDER
    | typeof OPENAI_PROVIDER
    | typeof OLLAMA_PROVIDER
    | undefined;
}

async function showConnectionMenu(
  context: vscode.ExtensionContext,
  deps: CommandDeps,
  placeHolder = "Configure provider credentials, env file, or API endpoint",
  setupOnly = false,
): Promise<boolean> {
  const items: ConnectionAction[] = [
    {
      id: "googleSecret",
      label: "$(key) Store Google key",
      description: "Use SecretStorage for GOOGLE_API_KEY",
      detail: `Provider: ${GOOGLE_PROVIDER} | Model: ${DEFAULT_GOOGLE_MODEL}`,
    },
    {
      id: "openrouterSecret",
      label: "$(key) Store OpenRouter key",
      description: "Use SecretStorage for OPENROUTER_API_KEY",
      detail: `Provider: ${OPENROUTER_PROVIDER} | Model: ${DEFAULT_OPENROUTER_MODEL}`,
    },
    {
      id: "openaiSecret",
      label: "$(key) Store OpenAI key",
      description: "Use SecretStorage for OPENAI_API_KEY",
      detail: `Provider: ${OPENAI_PROVIDER} | Model: ${DEFAULT_OPENAI_MODEL}`,
    },
    {
      id: "envFile",
      label: "$(file-code) Use environment file",
      description: "Paste or browse to an env file path",
      detail: `Default: ${getEnvironmentFileSetting() || DEFAULT_ENVIRONMENT_FILE}`,
    },
    {
      id: "processEnv",
      label: "$(terminal) Use process environment",
      description: "Read provider credentials from the current shell",
    },
    {
      id: "envTemplate",
      label: "$(new-file) Create env template",
      description: "Generate a Google, OpenRouter, OpenAI, or Ollama profile file",
    },
  ];

  if (!setupOnly) {
    items.push(
      {
        id: "openrouterSettings",
        label: "$(globe) Configure OpenRouter endpoint",
        description: "Base URL, model, referer, and title",
      },
      {
        id: "openaiSettings",
        label: "$(sparkle) Configure OpenAI image profile",
        description: "Base URL, image model, vision model, and size",
      },
      {
        id: "ollamaSettings",
        label: "$(server-process) Configure Ollama profile",
        description: "Configure local endpoint and model settings",
        detail: "Supports local SVG figure generation and vision-based evaluation",
      },
    );
  }

  const picked = await vscode.window.showQuickPick(items, { placeHolder });
  if (!picked) {
    return false;
  }

  if (picked.id === "googleSecret") {
    return configureSecretStorageProvider(context, deps, GOOGLE_PROVIDER);
  }
  if (picked.id === "openrouterSecret") {
    return configureSecretStorageProvider(context, deps, OPENROUTER_PROVIDER);
  }
  if (picked.id === "openaiSecret") {
    return configureSecretStorageProvider(context, deps, OPENAI_PROVIDER);
  }
  if (picked.id === "envFile") {
    return configureEnvironmentFileSource(context, deps);
  }
  if (picked.id === "processEnv") {
    return configureProcessEnvironmentSource(context, deps);
  }
  if (picked.id === "envTemplate") {
    return createEnvironmentFileTemplate(context, deps);
  }
  if (picked.id === "openrouterSettings") {
    return configureOpenRouterSettings(deps);
  }
  if (picked.id === "openaiSettings") {
    return configureOpenAiSettings(deps);
  }
  return configureOllamaSettings(deps);
}

async function configureSecretStorageProvider(
  context: vscode.ExtensionContext,
  deps: CommandDeps,
  provider: string,
): Promise<boolean> {
  await updateImageProviderSetting(provider);
  await updateCredentialSourceSetting(SECRET_STORAGE_SOURCE);

  const secretName = getSecretNameForProvider(provider);
  const existingValue = await context.secrets.get(secretName);
  if (existingValue) {
    const choice = await vscode.window.showQuickPick(
      [
        {
          label: "$(check) Keep existing key",
          description: `Reuse ${getApiKeyLabel(provider)} already stored in SecretStorage`,
        },
        {
          label: "$(edit) Replace stored key",
          description: "Paste a new value now",
        },
      ],
      {
        placeHolder: `SecretStorage already contains ${getApiKeyLabel(provider)}`,
      },
    );

    if (!choice) {
      return false;
    }
    if (choice.label.includes("Keep existing")) {
      await updateApiKeyContext(context);
      deps.mcpProvider.refresh();
      vscode.window.showInformationMessage(`${getApiKeyLabel(provider)} is active from SecretStorage.`);
      return true;
    }
  }

  const value = await vscode.window.showInputBox({
    ignoreFocusOut: true,
    password: true,
    placeHolder: `Paste ${getApiKeyLabel(provider)}`,
    prompt: `Store ${getApiKeyLabel(provider)} in VS Code SecretStorage`,
  });
  if (!value) {
    return false;
  }

  await context.secrets.store(secretName, value.trim());
  await updateApiKeyContext(context);
  deps.mcpProvider.refresh();
  vscode.window.showInformationMessage(`${getApiKeyLabel(provider)} stored in SecretStorage.`);
  return true;
}

async function configureEnvironmentFileSource(
  context: vscode.ExtensionContext,
  deps: CommandDeps,
): Promise<boolean> {
  const provider = await pickImageProvider("Choose the runtime image provider for env-file mode");
  if (!provider) {
    return false;
  }

  const configuredPath = await promptForEnvironmentFilePath(deps.workspaceRoot);
  if (!configuredPath) {
    return false;
  }

  await updateImageProviderSetting(provider);
  await updateCredentialSourceSetting(ENV_FILE_SOURCE);
  await updateEnvironmentFileSetting(configuredPath);

  const environmentFilePath = resolveEnvironmentFilePath(deps.workspaceRoot, configuredPath);
  if (!fs.existsSync(environmentFilePath)) {
    const createChoice = await vscode.window.showQuickPick(
      [
        {
          label: "$(new-file) Create env template now",
          description: `Write a ${provider} profile at ${configuredPath}`,
        },
        {
          label: "$(link-external) Keep the path only",
          description: "I will create or paste the file myself",
        },
      ],
      {
        placeHolder: `The env file ${configuredPath} does not exist yet`,
      },
    );

    if (!createChoice) {
      return false;
    }
    if (createChoice.label.includes("Create env template")) {
      const created = await createEnvironmentFileTemplate(context, deps, provider, configuredPath);
      if (!created) {
        return false;
      }
    }
  }

  await updateApiKeyContext(context);
  deps.mcpProvider.refresh();
  vscode.window.showInformationMessage(`Using env file ${configuredPath} for provider ${provider}.`);
  return true;
}

async function configureProcessEnvironmentSource(
  context: vscode.ExtensionContext,
  deps: CommandDeps,
): Promise<boolean> {
  const provider = await pickImageProvider("Choose the runtime image provider for process-env mode");
  if (!provider) {
    return false;
  }

  await updateImageProviderSetting(provider);
  await updateCredentialSourceSetting(PROCESS_ENV_SOURCE);
  await updateApiKeyContext(context);
  deps.mcpProvider.refresh();
  vscode.window.showInformationMessage(
    `Reading ${getApiKeyLabel(provider)} from the current shell environment for provider ${provider}.`,
  );
  return true;
}

async function configureOpenRouterSettings(deps: CommandDeps): Promise<boolean> {
  const config = vscode.workspace.getConfiguration("academicFiguresMcp");
  const baseUrl = await vscode.window.showInputBox({
    ignoreFocusOut: true,
    prompt: "OpenRouter base URL",
    value: config.get<string>("openRouterBaseUrl", DEFAULT_OPENROUTER_BASE_URL),
  });
  if (baseUrl === undefined) {
    return false;
  }

  const model = await vscode.window.showInputBox({
    ignoreFocusOut: true,
    prompt: "OpenRouter model ID",
    value: config.get<string>("openRouterModel", DEFAULT_OPENROUTER_MODEL),
  });
  if (model === undefined) {
    return false;
  }

  const referer = await vscode.window.showInputBox({
    ignoreFocusOut: true,
    prompt: "Optional OpenRouter HTTP-Referer header",
    value: config.get<string>("openRouterReferer", DEFAULT_OPENROUTER_REFERER),
  });
  if (referer === undefined) {
    return false;
  }

  const title = await vscode.window.showInputBox({
    ignoreFocusOut: true,
    prompt: "Optional OpenRouter X-OpenRouter-Title header",
    value: config.get<string>("openRouterTitle", DEFAULT_OPENROUTER_TITLE),
  });
  if (title === undefined) {
    return false;
  }

  const configuration = vscode.workspace.getConfiguration("academicFiguresMcp");
  const target = getConfigurationTarget();
  await configuration.update("openRouterBaseUrl", baseUrl.trim() || DEFAULT_OPENROUTER_BASE_URL, target);
  await configuration.update("openRouterModel", model.trim() || DEFAULT_OPENROUTER_MODEL, target);
  await configuration.update("openRouterReferer", referer.trim(), target);
  await configuration.update("openRouterTitle", title.trim() || DEFAULT_OPENROUTER_TITLE, target);
  deps.mcpProvider.refresh();
  vscode.window.showInformationMessage("OpenRouter endpoint settings updated.");
  return true;
}

async function configureOpenAiSettings(deps: CommandDeps): Promise<boolean> {
  const config = vscode.workspace.getConfiguration("academicFiguresMcp");
  const baseUrl = await vscode.window.showInputBox({
    ignoreFocusOut: true,
    prompt: "OpenAI API base URL",
    value: config.get<string>("openAiBaseUrl", DEFAULT_OPENAI_BASE_URL),
  });
  if (baseUrl === undefined) {
    return false;
  }

  const imageModel = await vscode.window.showInputBox({
    ignoreFocusOut: true,
    prompt: "OpenAI image model",
    value: config.get<string>("openAiModel", DEFAULT_OPENAI_MODEL),
  });
  if (imageModel === undefined) {
    return false;
  }

  const visionModel = await vscode.window.showInputBox({
    ignoreFocusOut: true,
    prompt: "OpenAI vision review model",
    value: config.get<string>("openAiVisionModel", DEFAULT_OPENAI_VISION_MODEL),
  });
  if (visionModel === undefined) {
    return false;
  }

  const imageSize = await vscode.window.showInputBox({
    ignoreFocusOut: true,
    prompt: "OpenAI Images API size hint",
    value: config.get<string>("openAiImageSize", DEFAULT_OPENAI_IMAGE_SIZE),
  });
  if (imageSize === undefined) {
    return false;
  }

  const target = getConfigurationTarget();
  await config.update("openAiBaseUrl", baseUrl.trim() || DEFAULT_OPENAI_BASE_URL, target);
  await config.update("openAiModel", imageModel.trim() || DEFAULT_OPENAI_MODEL, target);
  await config.update("openAiVisionModel", visionModel.trim() || DEFAULT_OPENAI_VISION_MODEL, target);
  await config.update("openAiImageSize", imageSize.trim() || DEFAULT_OPENAI_IMAGE_SIZE, target);
  const activate = await vscode.window.showQuickPick(
    [
      {
        label: "$(plug) Use OpenAI now",
        description: "Switch the active provider to OpenAI Images API",
      },
      {
        label: "$(check) Save settings only",
        description: "Keep the current provider unchanged",
      },
    ],
    { placeHolder: "Apply the updated OpenAI profile now?" },
  );
  if (activate?.label.includes("Use OpenAI now")) {
    await updateImageProviderSetting(OPENAI_PROVIDER);
  }
  deps.mcpProvider.refresh();
  vscode.window.showInformationMessage("OpenAI image profile updated.");
  return true;
}

async function configureOllamaSettings(deps: CommandDeps): Promise<boolean> {
  const config = vscode.workspace.getConfiguration("academicFiguresMcp");
  const baseUrl = await vscode.window.showInputBox({
    ignoreFocusOut: true,
    prompt: "Ollama OpenAI-compatible base URL",
    value: config.get<string>("ollamaBaseUrl", DEFAULT_OLLAMA_BASE_URL),
  });
  if (baseUrl === undefined) {
    return false;
  }

  const model = await vscode.window.showInputBox({
    ignoreFocusOut: true,
    prompt: "Ollama model name",
    value: config.get<string>("ollamaModel", DEFAULT_OLLAMA_MODEL),
  });
  if (model === undefined) {
    return false;
  }

  const target = getConfigurationTarget();
  await config.update("ollamaBaseUrl", baseUrl.trim() || DEFAULT_OLLAMA_BASE_URL, target);
  await config.update("ollamaModel", model.trim() || DEFAULT_OLLAMA_MODEL, target);
  const activate = await vscode.window.showQuickPick(
    [
      {
        label: "$(plug) Use Ollama now",
        description: "Switch the active provider to Ollama",
      },
      {
        label: "$(check) Save settings only",
        description: "Keep the current provider unchanged",
      },
    ],
    { placeHolder: "Apply the updated Ollama profile now?" },
  );
  if (activate?.label.includes("Use Ollama now")) {
    await updateImageProviderSetting(OLLAMA_PROVIDER);
  }
  deps.mcpProvider.refresh();
  vscode.window.showInformationMessage("Ollama profile updated.");
  return true;
}

async function createEnvironmentFileTemplate(
  context: vscode.ExtensionContext,
  deps: CommandDeps,
  forcedKind?: EnvironmentTemplateKind,
  forcedPath?: string,
): Promise<boolean> {
  const kind = forcedKind ?? (await pickEnvironmentTemplateKind());
  if (!kind) {
    return false;
  }

  const configuredPath = forcedPath ?? (await promptForEnvironmentFilePath(deps.workspaceRoot));
  if (!configuredPath) {
    return false;
  }

  const filePath = resolveEnvironmentFilePath(deps.workspaceRoot, configuredPath);
  if (fs.existsSync(filePath)) {
    const overwrite = await vscode.window.showWarningMessage(
      `${configuredPath} already exists. Overwrite it?`,
      "Overwrite",
      "Open Existing",
      "Cancel",
    );
    if (overwrite === "Cancel" || overwrite === undefined) {
      return false;
    }
    if (overwrite === "Open Existing") {
      const document = await vscode.workspace.openTextDocument(filePath);
      await vscode.window.showTextDocument(document, { preview: false });
      return false;
    }
  }

  const apiKey = await promptForTemplateApiKey(kind);
  if (apiKey === undefined) {
    return false;
  }

  fs.mkdirSync(path.dirname(filePath), { recursive: true });
  fs.writeFileSync(
    filePath,
    buildEnvironmentTemplate(kind, apiKey),
    "utf8",
  );

  const document = await vscode.workspace.openTextDocument(filePath);
  await vscode.window.showTextDocument(document, { preview: false });

  const activateChoice = await vscode.window.showQuickPick(
    [
      {
        label: "$(plug) Use this env file now",
        description: `Switch the extension to env-file mode with provider ${kind}`,
      },
      {
        label: "$(check) Create only",
        description: "Keep current provider and credential source",
      },
    ],
    {
      placeHolder: `Created ${configuredPath}`,
    },
  );

  if (activateChoice?.label.includes("Use this env file now")) {
    await updateEnvironmentFileSetting(configuredPath);
    await updateCredentialSourceSetting(ENV_FILE_SOURCE);
    await updateImageProviderSetting(kind);
    await updateApiKeyContext(context);
    deps.mcpProvider.refresh();
    vscode.window.showInformationMessage(`Created ${configuredPath} and switched the extension to env-file mode.`);
    return true;
  }

  vscode.window.showInformationMessage(`Created environment template at ${configuredPath}.`);
  return true;
}

async function pickEnvironmentTemplateKind(): Promise<EnvironmentTemplateKind | undefined> {
  const picked = await vscode.window.showQuickPick(
    [
      {
        label: GOOGLE_PROVIDER,
        description: "GOOGLE_API_KEY + GEMINI_MODEL",
      },
      {
        label: OPENROUTER_PROVIDER,
        description: "OPENROUTER_API_KEY + OpenRouter headers",
      },
      {
        label: OPENAI_PROVIDER,
        description: "OPENAI_API_KEY + OpenAI Images API settings",
      },
      {
        label: OLLAMA_PROVIDER,
        description: "Store local OpenAI-compatible endpoint settings",
      },
    ],
    {
      placeHolder: "Choose the type of environment template to create",
    },
  );
  return picked?.label as EnvironmentTemplateKind | undefined;
}

async function promptForTemplateApiKey(kind: EnvironmentTemplateKind): Promise<string | undefined> {
  if (kind === OLLAMA_PROVIDER) {
    return "";
  }

  const action = await vscode.window.showQuickPick(
    [
      {
        label: "$(edit) Paste key now",
        description: `Write ${getApiKeyLabel(kind)} into the new env file`,
      },
      {
        label: "$(symbol-string) Leave placeholder",
        description: `Create ${getApiKeyLabel(kind)}= and fill it later`,
      },
    ],
    {
      placeHolder: `Choose how to populate ${getApiKeyLabel(kind)}`,
    },
  );
  if (!action) {
    return undefined;
  }
  if (action.label.includes("Leave placeholder")) {
    return "";
  }

  const value = await vscode.window.showInputBox({
    ignoreFocusOut: true,
    password: true,
    placeHolder: `Paste ${getApiKeyLabel(kind)}`,
    prompt: `Value for ${getApiKeyLabel(kind)}`,
  });
  return value?.trim() ?? undefined;
}

function buildEnvironmentTemplate(kind: EnvironmentTemplateKind, apiKey: string): string {
  const config = vscode.workspace.getConfiguration("academicFiguresMcp");

  if (kind === GOOGLE_PROVIDER) {
    return [
      "# Academic Figures MCP environment profile",
      `AFM_IMAGE_PROVIDER=${GOOGLE_PROVIDER}`,
      `GOOGLE_API_KEY=${apiKey}`,
      `GEMINI_MODEL=${config.get<string>("googleModel", DEFAULT_GOOGLE_MODEL)}`,
      "",
    ].join("\n");
  }

  if (kind === OPENROUTER_PROVIDER) {
    return [
      "# Academic Figures MCP environment profile",
      `AFM_IMAGE_PROVIDER=${OPENROUTER_PROVIDER}`,
      `OPENROUTER_API_KEY=${apiKey}`,
      `OPENROUTER_BASE_URL=${config.get<string>("openRouterBaseUrl", DEFAULT_OPENROUTER_BASE_URL)}`,
      `OPENROUTER_HTTP_REFERER=${config.get<string>("openRouterReferer", DEFAULT_OPENROUTER_REFERER)}`,
      `OPENROUTER_APP_TITLE=${config.get<string>("openRouterTitle", DEFAULT_OPENROUTER_TITLE)}`,
      `GEMINI_MODEL=${config.get<string>("openRouterModel", DEFAULT_OPENROUTER_MODEL)}`,
      "",
    ].join("\n");
  }

  if (kind === OPENAI_PROVIDER) {
    return [
      "# Academic Figures MCP environment profile",
      `AFM_IMAGE_PROVIDER=${OPENAI_PROVIDER}`,
      `OPENAI_API_KEY=${apiKey}`,
      `OPENAI_IMAGE_MODEL=${config.get<string>("openAiModel", DEFAULT_OPENAI_MODEL)}`,
      `OPENAI_BASE_URL=${config.get<string>("openAiBaseUrl", DEFAULT_OPENAI_BASE_URL)}`,
      `OPENAI_VISION_MODEL=${config.get<string>("openAiVisionModel", DEFAULT_OPENAI_VISION_MODEL)}`,
      `OPENAI_IMAGE_SIZE=${config.get<string>("openAiImageSize", DEFAULT_OPENAI_IMAGE_SIZE)}`,
      "",
    ].join("\n");
  }

  return [
    "# Academic Figures MCP environment profile",
    `AFM_IMAGE_PROVIDER=${OLLAMA_PROVIDER}`,
    `OLLAMA_BASE_URL=${config.get<string>("ollamaBaseUrl", DEFAULT_OLLAMA_BASE_URL)}`,
    `OLLAMA_MODEL=${config.get<string>("ollamaModel", DEFAULT_OLLAMA_MODEL)}`,
    "",
  ].join("\n");
}

async function promptForEnvironmentFilePath(workspaceRoot: string | undefined): Promise<string | undefined> {
  const current = getEnvironmentFileSetting() || DEFAULT_ENVIRONMENT_FILE;
  const choice = await vscode.window.showQuickPick(
    [
      {
        label: "$(edit) Paste path manually",
        description: current,
      },
      {
        label: "$(folder-opened) Browse for a file",
        description: workspaceRoot ?? process.cwd(),
      },
    ],
    {
      placeHolder: "Choose how to provide the env file path",
    },
  );
  if (!choice) {
    return undefined;
  }

  if (choice.label.includes("Browse")) {
    const selected = await vscode.window.showOpenDialog({
      canSelectFiles: true,
      canSelectFolders: false,
      canSelectMany: false,
      defaultUri: vscode.Uri.file(resolveEnvironmentFilePath(workspaceRoot, current)),
      openLabel: "Use env file",
    });
    if (!selected?.[0]) {
      return undefined;
    }
    return toConfiguredEnvironmentPath(selected[0].fsPath, workspaceRoot);
  }

  const manual = await vscode.window.showInputBox({
    ignoreFocusOut: true,
    prompt: "Environment file path",
    value: current,
    placeHolder: DEFAULT_ENVIRONMENT_FILE,
  });
  return manual?.trim() || undefined;
}
