import assert from "node:assert/strict";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { afterEach, beforeEach, describe, it } from "node:test";

import {
  buildAcademicFiguresCodexServerSpec,
  getCodexConfigPath,
  getCodexHome,
  installCodexMcpServer,
} from "../codexConfig";

describe("codexConfig", () => {
  let originalCodexHome: string | undefined;
  let tempRoot: string;
  let codexHome: string;

  beforeEach(() => {
    originalCodexHome = process.env.CODEX_HOME;
    tempRoot = fs.mkdtempSync(path.join(os.tmpdir(), "afm-codex-config-"));
    codexHome = path.join(tempRoot, ".codex");
    process.env.CODEX_HOME = codexHome;
  });

  afterEach(() => {
    if (originalCodexHome === undefined) {
      delete process.env.CODEX_HOME;
    } else {
      process.env.CODEX_HOME = originalCodexHome;
    }
    fs.rmSync(tempRoot, { recursive: true, force: true });
  });

  it("honors CODEX_HOME when resolving the config path", () => {
    assert.equal(getCodexHome(), codexHome);
    assert.equal(getCodexConfigPath(), path.join(codexHome, "config.toml"));
  });

  it("does not create a Codex config unless Codex exists or force is enabled", () => {
    const spec = buildAcademicFiguresCodexServerSpec({
      packageName: "academic-figures-mcp",
      version: "0.4.5",
    });

    assert.equal(installCodexMcpServer(spec), false);
    assert.equal(fs.existsSync(getCodexConfigPath()), false);
  });

  it("adds the managed server while preserving unrelated Codex settings", () => {
    fs.mkdirSync(codexHome, { recursive: true });
    fs.writeFileSync(
      getCodexConfigPath(),
      [
        'model = "gpt-5.5"',
        "# keep this user comment",
        "[mcp_servers.pencil]",
        'command = "pencil"',
        'args = ["--app", "code"]',
        "",
      ].join("\n"),
      "utf8",
    );
    const spec = buildAcademicFiguresCodexServerSpec({
      packageName: "academic-figures-mcp",
      version: "0.4.5",
      env: {
        AFM_IMAGE_PROVIDER: "openai",
        OPENAI_IMAGE_MODEL: "gpt-image-2",
      },
    });

    assert.equal(installCodexMcpServer(spec), true);
    const updated = fs.readFileSync(getCodexConfigPath(), "utf8");

    assert.match(updated, /model = "gpt-5\.5"/u);
    assert.match(updated, /# keep this user comment/u);
    assert.match(updated, /\[mcp_servers\.pencil\]/u);
    assert.match(updated, /# Managed by Academic Figures MCP VS Code extension/u);
    assert.match(updated, /\[mcp_servers\.academic-figures\]/u);
    assert.match(
      updated,
      /args = \["--from", "academic-figures-mcp==0\.4\.5", "afm-server"\]/u,
    );
    assert.match(updated, /\[mcp_servers\.academic-figures\.env\]/u);
    assert.match(updated, /AFM_IMAGE_PROVIDER = "openai"/u);
    assert.match(updated, /OPENAI_IMAGE_MODEL = "gpt-image-2"/u);
    assert.equal(installCodexMcpServer(spec), false);
  });

  it("preserves a user-owned academic-figures server when the managed comment is absent", () => {
    fs.mkdirSync(codexHome, { recursive: true });
    const original = [
      "[mcp_servers.academic-figures]",
      'command = "custom-afm"',
      'args = ["serve", "--custom"]',
      "",
    ].join("\n");
    fs.writeFileSync(getCodexConfigPath(), original, "utf8");

    const spec = buildAcademicFiguresCodexServerSpec({
      packageName: "academic-figures-mcp",
      version: "0.4.5",
    });

    assert.equal(installCodexMcpServer(spec), false);
    assert.equal(fs.readFileSync(getCodexConfigPath(), "utf8"), original);
  });

  it("replaces stale managed tables without touching following servers", () => {
    fs.mkdirSync(codexHome, { recursive: true });
    fs.writeFileSync(
      getCodexConfigPath(),
      [
        "# Managed by Academic Figures MCP VS Code extension. Remove this block to opt out.",
        "[mcp_servers.academic-figures-mcp]",
        'command = "old"',
        'args = ["old"]',
        "",
        "[mcp_servers.academic-figures-mcp.env]",
        'OLD_VALUE = "gone"',
        "",
        "[mcp_servers.keep-me]",
        'command = "kept"',
        "",
      ].join("\n"),
      "utf8",
    );

    const spec = buildAcademicFiguresCodexServerSpec({
      packageName: "academic-figures-mcp",
      version: "0.4.6",
    });
    assert.equal(installCodexMcpServer(spec), true);
    const updated = fs.readFileSync(getCodexConfigPath(), "utf8");

    assert.doesNotMatch(updated, /OLD_VALUE/u);
    assert.doesNotMatch(updated, /command = "old"/u);
    assert.doesNotMatch(updated, /\[mcp_servers\.academic-figures-mcp\]/u);
    assert.match(updated, /\[mcp_servers\.keep-me\]/u);
    assert.match(updated, /command = "kept"/u);
    assert.match(updated, /academic-figures-mcp==0\.4\.6/u);
    assert.equal(
      [...updated.matchAll(/Managed by Academic Figures MCP VS Code extension/gu)].length,
      1,
    );
  });
});
