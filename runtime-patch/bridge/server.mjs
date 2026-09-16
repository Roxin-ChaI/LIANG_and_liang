/** Project-owned Unix socket server; no Electron or native Pet dependencies. */
import fs from "node:fs/promises";
import net from "node:net";
import path from "node:path";

import {
  BridgeProtocolError, MAX_MESSAGE_BYTES, defaultSocketPath, errorResponse,
  parseRequestLine, successResponse,
} from "./protocol.mjs";

const MAX_HISTORY = 1024;
const CLIENT_IDLE_MS = 10_000;
const MAX_CLIENTS = 32;
const MAX_REQUESTS_PER_CLIENT = 64;

function bridgeError(code, message) {
  const error = new Error(message);
  error.code = code;
  return error;
}
async function lstatOrNull(file) {
  try { return await fs.lstat(file); } catch (error) {
    if (error.code === "ENOENT") return null;
    throw error;
  }
}
function ownedPrivateDirectory(stat) {
  return stat.isDirectory() && stat.uid === process.getuid() && (stat.mode & 0o077) === 0;
}
function ownedPrivateSocket(stat) {
  return stat.isSocket() && stat.uid === process.getuid() && (stat.mode & 0o077) === 0;
}

async function probeExistingSocket(socketPath) {
  return new Promise((resolve, reject) => {
    const client = net.createConnection(socketPath);
    const timer = setTimeout(() => { client.destroy(); reject(bridgeError("SOCKET_PROBE_TIMEOUT", "Socket probe timed out")); }, 800);
    client.once("connect", () => {
      clearTimeout(timer); client.destroy(); reject(bridgeError("SOCKET_ACTIVE", "Socket is already active"));
    });
    client.once("error", (error) => {
      clearTimeout(timer); client.destroy();
      if (error.code === "ECONNREFUSED" || error.code === "ENOENT") resolve(error.code);
      else reject(bridgeError("SOCKET_PROBE_FAILED", "Socket ownership could not be confirmed"));
    });
  });
}

async function recoverStaleSocket(socketPath) {
  const initial = await lstatOrNull(socketPath);
  if (initial === null) return;
  if (!ownedPrivateSocket(initial)) {
    throw bridgeError("SOCKET_NOT_OWNED", "Refusing to replace a non-private owned socket");
  }
  const probe = await probeExistingSocket(socketPath);
  const current = await lstatOrNull(socketPath);
  if (probe === "ENOENT" && current === null) return;
  if (!current || !ownedPrivateSocket(current) || current.dev !== initial.dev || current.ino !== initial.ino) {
    throw bridgeError("SOCKET_CHANGED", "Socket changed during stale recovery");
  }
  await fs.unlink(socketPath);
}

function listen(server, socketPath) {
  return new Promise((resolve, reject) => {
    const onError = (error) => { server.off("listening", onListen); reject(error); };
    const onListen = () => { server.off("error", onError); resolve(); };
    server.once("error", onError); server.once("listening", onListen);
    server.listen(socketPath);
  });
}
function close(server) {
  return new Promise((resolve, reject) => {
    server.close((error) => error ? reject(error) : resolve());
  });
}

export function createBridgeServer({
  socketPath = defaultSocketPath(), dispatch, maxMessageBytes = MAX_MESSAGE_BYTES,
  dispatchTimeoutMs = 5000,
} = {}) {
  if (typeof socketPath !== "string" || !path.isAbsolute(socketPath)
      || Buffer.byteLength(socketPath, "utf8") > 100 || socketPath.includes("\0")) {
    throw new TypeError("socketPath must be an absolute, short Unix socket path");
  }
  if (typeof dispatch !== "function") throw new TypeError("dispatch must be a function");
  if (!Number.isInteger(maxMessageBytes) || maxMessageBytes < 64 || maxMessageBytes > MAX_MESSAGE_BYTES) {
    throw new TypeError("maxMessageBytes must be within 64..4096");
  }
  if (!Number.isInteger(dispatchTimeoutMs) || dispatchTimeoutMs < 10 || dispatchTimeoutMs > 10_000) {
    throw new TypeError("dispatchTimeoutMs must be within 10..10000");
  }
  const clients = new Set();
  const history = new Map();
  let server = null;
  let boundStat = null;
  let createdParent = false;

  async function ensureParent() {
    const parent = path.dirname(socketPath);
    let stat = await lstatOrNull(parent);
    if (stat === null) {
      await fs.mkdir(parent, { mode: 0o700 });
      createdParent = true;
      stat = await fs.lstat(parent);
    }
    if (!ownedPrivateDirectory(stat)) {
      throw bridgeError("SOCKET_PARENT_UNSAFE", "Socket directory must be owned and private");
    }
  }

  async function removeBoundSocket() {
    const stat = await lstatOrNull(socketPath);
    if (stat === null) return;
    if (boundStat && ownedPrivateSocket(stat) && stat.dev === boundStat.dev && stat.ino === boundStat.ino) {
      await fs.unlink(socketPath);
    } else {
      throw bridgeError("SOCKET_CHANGED", "Refusing to remove a different socket");
    }
  }
  async function removeCreatedParentIfEmpty() {
    if (!createdParent) return;
    try { await fs.rmdir(path.dirname(socketPath)); }
    catch (error) { if (error.code !== "ENOTEMPTY" && error.code !== "ENOENT") throw error; }
    createdParent = false;
  }

  async function start() {
    if (server !== null) throw bridgeError("ALREADY_STARTED", "Bridge is already started");
    try {
      await ensureParent();
      await recoverStaleSocket(socketPath);
    } catch (error) {
      await removeCreatedParentIfEmpty();
      throw error;
    }
    server = net.createServer((client) => {
      if (clients.size >= MAX_CLIENTS) { client.destroy(); return; }
      clients.add(client);
      client.setTimeout(CLIENT_IDLE_MS, () => client.destroy());
      client.once("close", () => clients.delete(client));
      let buffered = Buffer.alloc(0);
      let pending = Promise.resolve();
      let terminal = false;
      let requestCount = 0;

      async function handle(line) {
        let command;
        try { command = parseRequestLine(line, maxMessageBytes); }
        catch (error) {
          const response = errorResponse(error instanceof BridgeProtocolError ? error.code : "DISPATCH_FAILED", error.requestId);
          client.write(`${JSON.stringify(response)}\n`);
          return;
        }
        const canonical = `${command.target}:${command.animate}`;
        let record = history.get(command.requestId);
        if (record && record.canonical !== canonical) {
          client.write(`${JSON.stringify(errorResponse("DUPLICATE_REQUEST_ID", command.requestId))}\n`);
          return;
        }
        if (!record) {
          let timer;
          const timedDispatch = Promise.race([
            Promise.resolve().then(() => dispatch(command)),
            new Promise((_, reject) => {
              timer = setTimeout(() => reject(new BridgeProtocolError(
                "RUNTIME_TIMEOUT", "Runtime did not respond in time", command.requestId,
              )), dispatchTimeoutMs);
            }),
          ]).finally(() => clearTimeout(timer));
          const promise = timedDispatch.then((result) => successResponse(command, result))
            .catch((error) => errorResponse(
              error instanceof BridgeProtocolError ? error.code : error?.code, command.requestId,
            ));
          record = { canonical, promise };
          history.set(command.requestId, record);
          while (history.size > MAX_HISTORY) history.delete(history.keys().next().value);
        }
        const response = await record.promise;
        if (!client.destroyed) client.write(`${JSON.stringify(response)}\n`);
      }

      client.on("data", (chunk) => {
        if (terminal) return;
        if (chunk.length > maxMessageBytes * MAX_REQUESTS_PER_CLIENT) {
          terminal = true;
          client.write(`${JSON.stringify(errorResponse("MESSAGE_TOO_LARGE"))}\n`, () => client.destroy());
          return;
        }
        buffered = Buffer.concat([buffered, chunk]);
        while (true) {
          const index = buffered.indexOf(0x0a);
          if (index === -1) break;
          const line = buffered.subarray(0, index);
          buffered = buffered.subarray(index + 1);
          requestCount += 1;
          if (line.length > maxMessageBytes || requestCount > MAX_REQUESTS_PER_CLIENT) {
            terminal = true; break;
          }
          pending = pending.then(() => handle(line.toString("utf8"))).catch(() => {
            if (!client.destroyed) client.write(`${JSON.stringify(errorResponse("DISPATCH_FAILED"))}\n`);
          });
        }
        if (buffered.length > maxMessageBytes || terminal) {
          terminal = true;
          client.write(`${JSON.stringify(errorResponse("MESSAGE_TOO_LARGE"))}\n`, () => client.destroy());
        }
      });
    });
    try {
      await listen(server, socketPath);
      await fs.chmod(socketPath, 0o600);
      boundStat = await fs.lstat(socketPath);
      if (!ownedPrivateSocket(boundStat)) throw bridgeError("SOCKET_MODE_FAILED", "Socket is not 0600 and owned");
      return Object.freeze({ socketPath, socketMode: boundStat.mode & 0o777 });
    } catch (error) {
      for (const client of clients) client.destroy();
      if (server.listening) await close(server);
      server = null;
      await removeBoundSocket();
      await removeCreatedParentIfEmpty();
      throw error;
    }
  }

  async function stop() {
    if (server === null) return;
    for (const client of clients) client.destroy();
    if (server.listening) await close(server);
    server = null;
    await removeBoundSocket();
    await removeCreatedParentIfEmpty();
    history.clear();
  }
  return Object.freeze({ start, stop, socketPath });
}
