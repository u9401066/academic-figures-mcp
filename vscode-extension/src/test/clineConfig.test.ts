import assert from "node:assert/strict";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { afterEach, beforeEach, describe, it } from "node:test";

import {
  buildAcademicFiguresClineServerEntry,
  getClineMcpSettingsPath,
  installClineMcpServer,
} from "../clineConfig";

describe("clineConfig", () => {
  let tempRoot: string;
  let globalStorageRoot: string;
  let settingsPath: string;

  beforeEach(() => {
    tempRoot = fs.mkdtempSync(path.join(os.tmpdir(), "afm-cline-config-"));
    globalStorageRoot = path.join(tempRoot, "globalStorage", "u9401066.academic-figures-mcp");
    settingsPath = getClineMcpSettingsPath(globalStorageRoot);
  });

  afterEach(() => {
    fs.rmSync(tempRoot, { recursive: true, force: true });
  });

  it("preserves unrelated servers and Cline alwaysAllow metadata", () => {
    fs.mkdirSync(path.dirname(settingsPath), { recursive: true });
    fs.writeFileSync(
      settingsPath,
      JSON.stringify(
        {
          mcpServers: {
            "academic-figures": {
              command: "old",
              args: ["old", "afm-server"],
              alwaysAllow: ["generate_figure"],
              disabled: true,
            },
            "keep-me": {
              command: "kept",
              args: ["server"],
            },
          },
        },
        null,
        2,
      ),
      "utf8",
    );

    const entry = buildAcademicFiguresClineServerEntry({
      packageName: "academic-figures-mcp",
      version: "0.4.5",
      env: { AFM_IMAGE_PROVIDER: "openai" },
    });

    assert.equal(installClineMcpServer(settingsPath, entry), true);
    const updated = JSON.parse(fs.readFileSync(settingsPath, "utf8")) as {
      mcpServers: Record<string, { args: string[]; alwaysAllow?: string[]; command: string; disabled?: boolean; env?: Record<string, string> }>;
    };

    assert.equal(updated.mcpServers["keep-me"].command, "kept");
    assert.equal(updated.mcpServers["academic-figures"].command, "uvx");
    assert.deepEqual(updated.mcpServers["academic-figures"].alwaysAllow, ["generate_figure"]);
    assert.equal(updated.mcpServers["academic-figures"].disabled, true);
    assert.deepEqual(updated.mcpServers["academic-figures"].args, [
      "--from",
      "academic-figures-mcp==0.4.5",
      "afm-server",
    ]);
    assert.deepEqual(updated.mcpServers["academic-figures"].env, {
      AFM_IMAGE_PROVIDER: "openai",
    });
    assert.equal(installClineMcpServer(settingsPath, entry), false);
  });

  it("preserves a user-owned same-key Cline server entry", () => {
    fs.mkdirSync(path.dirname(settingsPath), { recursive: true });
    const original = JSON.stringify(
      {
        mcpServers: {
          "academic-figures": {
            command: "custom-afm",
            args: ["serve", "--custom"],
            env: {
              CUSTOM_VALUE: "keep",
            },
          },
        },
      },
      null,
      2,
    ) + "\n";
    fs.writeFileSync(settingsPath, original, "utf8");

    const entry = buildAcademicFiguresClineServerEntry({
      packageName: "academic-figures-mcp",
      version: "0.4.5",
    });

    assert.equal(installClineMcpServer(settingsPath, entry), false);
    assert.equal(fs.readFileSync(settingsPath, "utf8"), original);
  });

  it("does not overwrite invalid Cline settings", () => {
    fs.mkdirSync(path.dirname(settingsPath), { recursive: true });
    fs.writeFileSync(settingsPath, "{ invalid", "utf8");

    const entry = buildAcademicFiguresClineServerEntry({
      packageName: "academic-figures-mcp",
      version: "0.4.5",
    });

    assert.equal(installClineMcpServer(settingsPath, entry), false);
    assert.equal(fs.readFileSync(settingsPath, "utf8"), "{ invalid");
  });
});
