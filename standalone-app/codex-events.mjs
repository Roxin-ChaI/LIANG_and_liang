/** Verified Desktop Hook metadata only; no prompts, tool arguments or outputs. */
import fs from "node:fs/promises";
import net from "node:net";
import path from "node:path";

export const VERIFIED_EVENTS = Object.freeze(["SessionStart", "PreToolUse", "PostToolUse", "Stop"]);
const VERIFIED = new Set(VERIFIED_EVENTS);
const MAX_SESSIONS = 256;
const MAX_SEEN = 1024;

export function verifiedHookEvent(value) {
  if (!value || typeof value !== "object" || Array.isArray(value)
      || Object.keys(value).sort().join(",") !== "event,session_id,timestamp"
      || !VERIFIED.has(value.event)
      || typeof value.session_id !== "string" || !value.session_id || value.session_id.length > 256
      || typeof value.timestamp !== "string" || value.timestamp.length > 64
      || !Number.isFinite(Date.parse(value.timestamp))) return null;
  return Object.freeze({ event: value.event, session_id: value.session_id,
    timestamp: value.timestamp });
}

/** Stop ends a task; PostToolUse alone does not prove the turn is complete. */
export function createCodexSessionTracker({ now = Date.now, setTimer = setTimeout,
  clearTimer = clearTimeout, timeoutMs = 600_000, onState = () => {}, onEvent = () => {} } = {}) {
  if (!Number.isFinite(timeoutMs) || timeoutMs <= 0) throw new TypeError("timeoutMs must be positive");
  const sessions = new Map();
  const seen = new Map();
  let state = "idle";
  let timer = null;
  let closed = false;

  function publish(reason) {
    const next = [...sessions.values()].some((session) => session.working) ? "running" : "idle";
    if (next !== state) { state = next; onState(next, { reason }); }
  }
  function expire() {
    const current = now();
    for (const session of sessions.values()) {
      if (session.working && session.deadline <= current) {
        session.working = false;
        onEvent({ event: "Timeout", session_id: session.id, timestamp: new Date(current).toISOString() },
          { reason: "timeout", state: "idle" });
      }
    }
    publish("timeout");
    schedule();
  }
  function schedule() {
    if (timer !== null) clearTimer(timer);
    timer = null;
    if (closed) return;
    const deadlines = [...sessions.values()].filter((item) => item.working).map((item) => item.deadline);
    if (deadlines.length) timer = setTimer(expire, Math.max(1, Math.min(...deadlines) - now()));
  }
  function accept(value) {
    const event = verifiedHookEvent(value);
    if (closed || !event) return Object.freeze({ accepted: false, reason: "unsupported" });
    const key = `${event.session_id}\u0000${event.event}\u0000${event.timestamp}`;
    if (seen.has(key)) return Object.freeze({ accepted: false, reason: "duplicate" });
    const eventTime = Date.parse(event.timestamp);
    const existing = sessions.get(event.session_id);
    if (existing && eventTime < existing.lastEventTime) {
      return Object.freeze({ accepted: false, reason: "stale" });
    }
    seen.set(key, now());
    if (seen.size > MAX_SEEN) seen.delete(seen.keys().next().value);
    const session = existing ?? { id: event.session_id, working: false, deadline: 0,
      lastEventTime: -Infinity, lastSeen: 0, completedTools: 0 };
    session.lastEventTime = eventTime;
    session.lastSeen = now();
    if (event.event === "PreToolUse") {
      session.working = true;
      session.deadline = now() + timeoutMs;
    } else if (event.event === "PostToolUse") {
      session.completedTools += 1;
      if (session.working) session.deadline = now() + timeoutMs;
    } else if (event.event === "Stop") {
      session.working = false;
    }
    sessions.delete(event.session_id);
    sessions.set(event.session_id, session);
    if (sessions.size > MAX_SESSIONS) {
      const oldIdle = [...sessions].find(([, item]) => !item.working);
      if (oldIdle) sessions.delete(oldIdle[0]);
    }
    publish(event.event);
    schedule();
    const result = Object.freeze({ accepted: true, state, activeSessions:
      [...sessions.values()].filter((item) => item.working).length,
    completedTools: session.completedTools });
    onEvent(event, result);
    return result;
  }
  function stop() {
    closed = true;
    if (timer !== null) clearTimer(timer);
    timer = null;
  }
  return Object.freeze({ accept, stop, snapshot: () => Object.freeze({ state,
    activeSessions: [...sessions.values()].filter((item) => item.working).length }) });
}

/** Private Unix socket consumed by the existing Python hook receiver. */
export async function createHookForwardServer(socketPath, onEvent) {
  if (typeof onEvent !== "function") throw new TypeError("onEvent is required");
  await fs.mkdir(path.dirname(socketPath), { recursive: true });
  const server = net.createServer((client) => {
    let pending = "";
    client.setEncoding("utf8");
    client.setTimeout(1000, () => client.destroy());
    client.on("data", (chunk) => {
      pending += chunk;
      if (pending.length > 4096) { client.destroy(); return; }
      const end = pending.indexOf("\n");
      if (end < 0) return;
      try { onEvent(JSON.parse(pending.slice(0, end))); } catch { /* fail open */ }
      client.end();
    });
  });
  try {
    await new Promise((resolve, reject) => {
      server.once("error", reject);
      server.listen(socketPath, resolve);
    });
    await fs.chmod(socketPath, 0o600);
    const identity = await fs.lstat(socketPath);
    return Object.freeze({
      socketPath,
      async close() {
        await new Promise((resolve) => server.close(resolve));
        try {
          const current = await fs.lstat(socketPath);
          if (current.isSocket() && current.ino === identity.ino) await fs.unlink(socketPath);
        } catch (error) { if (error.code !== "ENOENT") throw error; }
      },
    });
  } catch (error) {
    server.close();
    throw error;
  }
}
