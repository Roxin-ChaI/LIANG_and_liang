import assert from "node:assert/strict";
import fs from "node:fs/promises";
import net from "node:net";
import os from "node:os";
import path from "node:path";
import test from "node:test";
import { createCodexSessionTracker, createHookForwardServer, verifiedHookEvent } from "./codex-events.mjs";

const base = Date.parse("2026-09-26T10:00:00.000Z");
function event(name, session = "desktop-1", offset = 0) {
  return { event: name, session_id: session, timestamp: new Date(base + offset).toISOString() };
}
function fakeClock() {
  let time = base;
  let scheduled = null;
  return {
    now: () => time,
    setTimer: (callback, delay) => { scheduled = { callback, at: time + delay }; return scheduled; },
    clearTimer: (timer) => { if (scheduled === timer) scheduled = null; },
    advance(ms) {
      time += ms;
      if (scheduled && scheduled.at <= time) { const { callback } = scheduled; scheduled = null; callback(); }
    },
  };
}

test("only the four Desktop-observed metadata events are accepted", () => {
  assert.deepEqual(verifiedHookEvent(event("SessionStart")), event("SessionStart"));
  for (const name of ["PermissionRequest", "UserPromptSubmit", "SessionEnd", "Waiting"]) {
    assert.equal(verifiedHookEvent(event(name)), null);
  }
  assert.equal(verifiedHookEvent({ ...event("Stop"), tool_input: "SECRET" }), null);
  assert.equal(verifiedHookEvent({ ...event("Stop"), timestamp: "invalid" }), null);
});

test("event replay enters Running on PreToolUse and Idle only on Stop", () => {
  const changes = [];
  const observed = [];
  const tracker = createCodexSessionTracker({ onState: (state) => changes.push(state),
    onEvent: (value) => observed.push(value.event) });
  for (const [name, offset] of [["SessionStart", 0], ["PreToolUse", 1],
    ["PostToolUse", 2], ["PreToolUse", 3], ["PostToolUse", 4], ["Stop", 5]]) {
    assert.equal(tracker.accept(event(name, "desktop-1", offset)).accepted, true);
  }
  assert.deepEqual(changes, ["running", "idle"]);
  assert.deepEqual(observed, ["SessionStart", "PreToolUse", "PostToolUse", "PreToolUse", "PostToolUse", "Stop"]);
  assert.equal(tracker.snapshot().activeSessions, 0);
  tracker.stop();
});

test("duplicate, stale, unverified and out-of-order tool events do not resurrect work", () => {
  const tracker = createCodexSessionTracker();
  assert.equal(tracker.accept(event("PostToolUse", "a", 1)).state, "idle");
  assert.equal(tracker.accept(event("PreToolUse", "a", 2)).state, "running");
  assert.equal(tracker.accept(event("PreToolUse", "a", 2)).reason, "duplicate");
  assert.equal(tracker.accept(event("Stop", "a", 3)).state, "idle");
  assert.equal(tracker.accept(event("PreToolUse", "a", 1)).reason, "stale");
  assert.equal(tracker.accept(event("PermissionRequest", "a", 4)).reason, "unsupported");
  assert.equal(tracker.snapshot().state, "idle");
  tracker.stop();
});

test("multiple sessions remain Running until all have stopped", () => {
  const tracker = createCodexSessionTracker();
  tracker.accept(event("PreToolUse", "one", 1));
  tracker.accept(event("PreToolUse", "two", 2));
  assert.equal(tracker.snapshot().activeSessions, 2);
  tracker.accept(event("Stop", "one", 3));
  assert.deepEqual(tracker.snapshot(), { state: "running", activeSessions: 1 });
  tracker.accept(event("Stop", "two", 4));
  assert.deepEqual(tracker.snapshot(), { state: "idle", activeSessions: 0 });
  tracker.stop();
});

test("missing Stop or receiver disconnect recovers by a single deadline timer", () => {
  const clock = fakeClock();
  const changes = [];
  const tracker = createCodexSessionTracker({ ...clock, timeoutMs: 100,
    onState: (state) => changes.push(state) });
  tracker.accept(event("PreToolUse"));
  clock.advance(90);
  tracker.accept(event("PostToolUse", "desktop-1", 1));
  clock.advance(99);
  assert.equal(tracker.snapshot().state, "running");
  clock.advance(1);
  assert.deepEqual(changes, ["running", "idle"]);
  tracker.stop();
});

test("forward socket accepts metadata and is private; failed connection recovers", async () => {
  const directory = await fs.mkdtemp(path.join(os.tmpdir(), "liang-hook-forward-"));
  const socketPath = path.join(directory, "forward.sock");
  const received = [];
  try {
    let server = await createHookForwardServer(socketPath, (value) => received.push(value));
    assert.equal((await fs.stat(socketPath)).mode & 0o777, 0o600);
    const send = (payload) => new Promise((resolve, reject) => {
      const client = net.createConnection(socketPath, () => client.end(`${JSON.stringify(payload)}\n`));
      client.on("error", reject);
      client.on("close", resolve);
    });
    await send(event("PreToolUse"));
    assert.deepEqual(received, [event("PreToolUse")]);
    await server.close();
    await assert.rejects(send(event("Stop")));
    server = await createHookForwardServer(socketPath, (value) => received.push(value));
    await send(event("Stop", "desktop-1", 1));
    assert.equal(received.length, 2);
    await server.close();
    await assert.rejects(fs.stat(socketPath), { code: "ENOENT" });
  } finally { await fs.rm(directory, { recursive: true, force: true }); }
});
