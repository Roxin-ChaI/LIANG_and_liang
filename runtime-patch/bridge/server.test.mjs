import assert from "node:assert/strict";
import fs from "node:fs/promises";
import net from "node:net";
import os from "node:os";
import path from "node:path";
import test from "node:test";

import { defaultSocketPath, parseRequestLine } from "./protocol.mjs";
import { createBridgeServer } from "./server.mjs";

function command(target = "gu", animate = true, requestId = "test-1") {
  return { protocolVersion: 1, requestId, method: "setTargetForm", params: { target, animate } };
}
function accepted(commandValue) {
  return {
    requestId: commandValue.requestId, accepted: true,
    currentForm: commandValue.target, targetForm: commandValue.target, transitioning: commandValue.animate,
  };
}
async function root(t) {
  const dir = await fs.mkdtemp(path.join(os.tmpdir(), "liang-bridge-test-"));
  t.after(() => fs.rm(dir, { recursive: true, force: true }));
  return dir;
}
async function ready(t, dispatch = accepted) {
  const socketPath = path.join(await root(t), "runtime.sock");
  const server = createBridgeServer({ socketPath, dispatch });
  await server.start();
  t.after(() => server.stop());
  return { server, socketPath };
}
function exchange(socketPath, lines) {
  return new Promise((resolve, reject) => {
    const socket = net.createConnection(socketPath);
    const responses = [];
    let buffer = "";
    const timer = setTimeout(() => { socket.destroy(); reject(Error("test socket timed out")); }, 2000);
    socket.once("error", (error) => { clearTimeout(timer); reject(error); });
    socket.once("connect", () => socket.write(lines.map((line) => `${line}\n`).join("")));
    socket.on("data", (chunk) => {
      buffer += chunk.toString("utf8");
      while (buffer.includes("\n")) {
        const index = buffer.indexOf("\n");
        responses.push(JSON.parse(buffer.slice(0, index)));
        buffer = buffer.slice(index + 1);
        if (responses.length === lines.length) {
          clearTimeout(timer); socket.end(); resolve(responses); return;
        }
      }
    });
  });
}
const send = async (socketPath, value) => (await exchange(socketPath, [JSON.stringify(value)]))[0];

test("valid Gu request is dispatched", async (t) => {
  const { socketPath } = await ready(t); const response = await send(socketPath, command("gu"));
  assert.deepEqual(response.result, { accepted: true, currentForm: "gu", targetForm: "gu", transitioning: true });
});
test("valid Feng request is dispatched", async (t) => {
  const { socketPath } = await ready(t); assert.equal((await send(socketPath, command("feng"))).result.targetForm, "feng");
});
test("animate=true is delivered without coercion", async (t) => {
  let seen; const { socketPath } = await ready(t, (value) => { seen = value; return accepted(value); });
  await send(socketPath, command("gu", true)); assert.equal(seen.animate, true);
});
test("animate=false is delivered without coercion", async (t) => {
  let seen; const { socketPath } = await ready(t, (value) => { seen = value; return accepted(value); });
  await send(socketPath, command("gu", false)); assert.equal(seen.animate, false);
});
test("invalid protocol is rejected", async (t) => {
  const { socketPath } = await ready(t); const value = command(); value.protocolVersion = 2;
  assert.equal((await send(socketPath, value)).error.code, "INVALID_PROTOCOL");
});
test("unknown method is rejected", async (t) => {
  const { socketPath } = await ready(t); const value = command(); value.method = "execute";
  assert.equal((await send(socketPath, value)).error.code, "UNKNOWN_METHOD");
});
test("invalid target is rejected", async (t) => {
  const { socketPath } = await ready(t);
  assert.equal((await send(socketPath, command("other"))).error.code, "INVALID_TARGET");
});
test("invalid animate type is rejected", async (t) => {
  const { socketPath } = await ready(t); const value = command(); value.params.animate = "yes";
  assert.equal((await send(socketPath, value)).error.code, "INVALID_ANIMATE");
});
test("extra top-level and nested properties are rejected", async (t) => {
  const { socketPath } = await ready(t); const top = command(); top.path = "/tmp/file";
  const nested = command("gu", true, "test-2"); nested.params.shell = "echo";
  assert.equal((await send(socketPath, top)).error.code, "INVALID_REQUEST");
  assert.equal((await send(socketPath, nested)).error.code, "INVALID_PARAMS");
});
test("malformed JSON and concatenated objects are rejected", async (t) => {
  const { socketPath } = await ready(t);
  assert.equal((await exchange(socketPath, ["{not-json"]))[0].error.code, "MALFORMED_JSON");
  assert.equal((await exchange(socketPath, ["{}{}"]))[0].error.code, "MALFORMED_JSON");
});
test("oversized line is rejected before dispatch", async (t) => {
  let calls = 0; const { socketPath } = await ready(t, (value) => { calls += 1; return accepted(value); });
  const response = (await exchange(socketPath, ["x".repeat(5000)]))[0];
  assert.equal(response.error.code, "MESSAGE_TOO_LARGE"); assert.equal(calls, 0);
});
test("empty requestId is rejected", async (t) => {
  const { socketPath } = await ready(t);
  assert.equal((await send(socketPath, command("gu", true, ""))).error.code, "INVALID_REQUEST_ID");
});
test("duplicate requestId reuses the same result and conflicting payload is rejected", async (t) => {
  let calls = 0; const { socketPath } = await ready(t, (value) => { calls += 1; return accepted(value); });
  const first = await send(socketPath, command("gu", true, "same-id"));
  const second = await send(socketPath, command("gu", true, "same-id"));
  const different = await send(socketPath, command("feng", true, "same-id"));
  assert.deepEqual(second, first); assert.equal(calls, 1); assert.equal(different.error.code, "DUPLICATE_REQUEST_ID");
});
test("socket is created with mode 0600", async (t) => {
  const { socketPath } = await ready(t); const stat = await fs.lstat(socketPath);
  assert.equal(stat.isSocket(), true); assert.equal(stat.mode & 0o777, 0o600); assert.equal(stat.uid, process.getuid());
});
test("clean shutdown removes only the bound socket", async (t) => {
  const { server, socketPath } = await ready(t); await server.stop();
  await assert.rejects(fs.lstat(socketPath), { code: "ENOENT" });
});
test("stale owned private socket is safely recovered", async (t) => {
  const dir = await root(t); const old = path.join(dir, "old.sock"); const socketPath = path.join(dir, "runtime.sock");
  const prior = net.createServer();
  await new Promise((resolve) => prior.listen(old, resolve));
  await fs.chmod(old, 0o600);
  await fs.rename(old, socketPath);
  await new Promise((resolve) => prior.close(resolve));
  assert.equal((await fs.lstat(socketPath)).isSocket(), true);
  const server = createBridgeServer({ socketPath, dispatch: accepted });
  await server.start(); t.after(() => server.stop());
  assert.equal((await send(socketPath, command())).ok, true);
});
test("ordinary file at socket path is never overwritten", async (t) => {
  const socketPath = path.join(await root(t), "runtime.sock");
  await fs.writeFile(socketPath, "business data");
  const server = createBridgeServer({ socketPath, dispatch: accepted });
  await assert.rejects(server.start(), { code: "SOCKET_NOT_OWNED" });
  assert.equal(await fs.readFile(socketPath, "utf8"), "business data");
});
test("non-private socket at path is not unlinked", async (t) => {
  const socketPath = path.join(await root(t), "runtime.sock"); const prior = net.createServer();
  await new Promise((resolve) => prior.listen(socketPath, resolve));
  await fs.chmod(socketPath, 0o666);
  const server = createBridgeServer({ socketPath, dispatch: accepted });
  await assert.rejects(server.start(), { code: "SOCKET_NOT_OWNED" });
  assert.equal((await fs.lstat(socketPath)).isSocket(), true);
  await new Promise((resolve) => prior.close(resolve));
});
test("multiple sequential requests on one client are framed separately", async (t) => {
  const { socketPath } = await ready(t);
  const values = await exchange(socketPath, [JSON.stringify(command("gu", true, "seq-1")), JSON.stringify(command("feng", false, "seq-2"))]);
  assert.deepEqual(values.map((value) => value.requestId), ["seq-1", "seq-2"]);
});
test("concurrent clients receive correlated responses", async (t) => {
  const { socketPath } = await ready(t);
  const values = await Promise.all(Array.from({ length: 8 }, (_, i) => send(socketPath, command(i % 2 ? "feng" : "gu", true, `client-${i}`))));
  assert.deepEqual(values.map((value) => value.requestId), Array.from({ length: 8 }, (_, i) => `client-${i}`));
});
test("dispatch exception has a fixed safe error, not a stack or path", async (t) => {
  const { socketPath } = await ready(t, () => { throw Error("secret /Applications/ChatGPT.app stack"); });
  const response = await send(socketPath, command());
  assert.equal(response.error.code, "DISPATCH_FAILED");
  assert.equal(JSON.stringify(response).includes("/Applications"), false);
});
test("nonresponsive dispatch produces correlated finite timeout", async (t) => {
  const socketPath = path.join(await root(t), "runtime.sock");
  const server = createBridgeServer({ socketPath, dispatch: () => new Promise(() => {}), dispatchTimeoutMs: 25 });
  await server.start(); t.after(() => server.stop());
  const response = await send(socketPath, command("feng", true, "timeout-id"));
  assert.deepEqual([response.requestId, response.error.code], ["timeout-id", "RUNTIME_TIMEOUT"]);
});
test("requestId has a hard length and control-character bound", async (t) => {
  const { socketPath } = await ready(t);
  assert.equal((await send(socketPath, command("gu", true, "a".repeat(129)))).error.code, "INVALID_REQUEST_ID");
  assert.equal((await send(socketPath, command("gu", true, "a\\nb"))).error.code, "INVALID_REQUEST_ID");
});
test("embedded raw newline and extra JSON objects are unambiguous", () => {
  assert.throws(() => parseRequestLine('{"requestId":"a\nb"}'), { code: "INVALID_FRAMING" });
  assert.throws(() => parseRequestLine('{}{}'), { code: "MALFORMED_JSON" });
});
test("default socket namespace is user-private and short", () => {
  const socketPath = defaultSocketPath();
  assert.equal(socketPath.includes(`liang-no-henshin-${process.getuid()}`), true);
  assert.equal(Buffer.byteLength(socketPath) <= 100, true);
  assert.equal(socketPath.includes(".codex/ipc"), false);
});
