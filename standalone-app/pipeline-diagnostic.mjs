/** Opt-in, metadata-only event pipeline trace. Never record hook payloads. */
import fs from "node:fs";
import path from "node:path";

const FIELDS = ["stage", "event", "sessionId", "accepted", "activeSessions",
  "state", "underlyingState", "row", "reason"];

export function createPipelineDiagnostic(file, { enabled = false, now = Date.now } = {}) {
  if (!enabled) return () => {};
  fs.mkdirSync(path.dirname(file), { recursive: true });
  return (entry) => {
    try {
      const record = { observedAt: now(), pid: process.pid };
      for (const field of FIELDS) {
        const value = entry?.[field];
        if (typeof value === "string" || typeof value === "boolean" || Number.isInteger(value)) {
          record[field] = value;
        }
      }
      const fd = fs.openSync(file, fs.constants.O_WRONLY | fs.constants.O_APPEND |
        fs.constants.O_CREAT | fs.constants.O_NOFOLLOW, 0o600);
      try {
        if ((fs.fstatSync(fd).mode & 0o777) !== 0o600) return;
        fs.writeSync(fd, `${JSON.stringify(record)}\n`);
      } finally { fs.closeSync(fd); }
    } catch { /* Diagnostics must never affect the pet or Hook path. */ }
  };
}
