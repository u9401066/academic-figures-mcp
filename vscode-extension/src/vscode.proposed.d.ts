import type { CancellationToken, Disposable, Event, ProviderResult, Uri } from "vscode";

declare module "vscode" {
  export interface McpStdioServerDefinition {
    label?: string;
    command: string;
    args?: string[];
    env?: Record<string, string>;
    cwd?: Uri;
  }

  export interface McpServerDefinitionProvider<T> {
    readonly onDidChangeMcpServerDefinitions?: Event<void>;
    provideMcpServerDefinitions(token: CancellationToken): ProviderResult<T[]>;
  }

  export namespace lm {
    function registerMcpServerDefinitionProvider(
      id: string,
      provider: McpServerDefinitionProvider<McpStdioServerDefinition>,
    ): Disposable;
  }
}