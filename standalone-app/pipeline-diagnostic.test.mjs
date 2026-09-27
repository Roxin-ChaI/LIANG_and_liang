import assert from "node:assert/strict";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import test from "node:test";
import { createPipelineDiagnostic } from "./pipeline-diagnostic.mjs";

test("opt-in trace records only allowed metadata with private permissions", () => {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), "liang-pipeline-"));
  try {
    const file = path.join(root, "trace.jsonl");
    createPipelineDiagnostic(file)({ stage: "ignored" });
    assert.equal(fs.existsSync(file), false);
    createPipelineDiagnostic(file, { enabled: true, now: () => 123 })({
      stage: "electron-received", event: "PreToolUse", sessionId: "desktop-1",
      prompt: "SECRET", tool_input: "SECRET", row: 7,
    });
    assert.equal(fs.statSync(file).mode & 0o777, 0o600);
    const saved = fs.readFileSync(file, "utf8");
    assert.equal(saved.includes("SECRET"), false);
    assert.deepEqual(JSON.parse(saved), { observedAt: 123, pid: process.pid,
      stage: "electron-received", event: "PreToolUse", sessionId: "desktop-1", row: 7 });
  } finally { fs.rmSync(root, { recursive: true, force: true }); }
});

test("trace refuses symlinks and permissive existing files", () => {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), "liang-pipeline-"));
  try {
    const target = path.join(root, "target");
    const file = path.join(root, "trace.jsonl");
    fs.writeFileSync(target, "unchanged");
    fs.symlinkSync(target, file);
    const trace = createPipelineDiagnostic(file, { enabled: true });
    trace({ stage: "ignored" });
    assert.equal(fs.readFileSync(target, "utf8"), "unchanged");
    fs.unlinkSync(file);
    fs.writeFileSync(file, "unchanged", { mode: 0o644 });
    trace({ stage: "ignored" });
    assert.equal(fs.readFileSync(file, "utf8"), "unchanged");
  } finally { fs.rmSync(root, { recursive: true, force: true }); }
});
