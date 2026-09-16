/** Narrow, newline-delimited Liang Pet control protocol v1. */
import os from "node:os";
import path from "node:path";

export const PROTOCOL_VERSION = 1;
export const MAX_MESSAGE_BYTES = 4096;
export const MAX_REQUEST_ID_LENGTH = 128;
export const SOCKET_NAMESPACE = "liang-no-henshin";

export class BridgeProtocolError extends Error {
  constructor(code, message, requestId = null) {
    super(message);
    this.name = "BridgeProtocolError";
    this.code = code;
    this.requestId = requestId;
  }
}

function object(value) { return value !== null && typeof value === "object" && !Array.isArray(value); }
function exactKeys(value, keys) {
  return object(value) && Object.keys(value).length === keys.length
    && keys.every((key) => Object.hasOwn(value, key));
}
function candidateRequestId(value) {
  return object(value) && validRequestId(value.requestId) ? value.requestId : null;
}
export function validRequestId(value) {
  return typeof value === "string" && value.length <= MAX_REQUEST_ID_LENGTH
    && /^[A-Za-z0-9._:-]+$/.test(value);
}

/** Reject all unknown fields and types; never reflect raw client input. */
export function parseRequestLine(line, maxMessageBytes = MAX_MESSAGE_BYTES) {
  if (typeof line !== "string" || Buffer.byteLength(line, "utf8") > maxMessageBytes) {
    throw new BridgeProtocolError("MESSAGE_TOO_LARGE", "Request exceeds the message limit");
  }
  if (line.length === 0 || line.includes("\n") || line.includes("\r")) {
    throw new BridgeProtocolError("INVALID_FRAMING", "Expected one JSON object per line");
  }
  let request;
  try { request = JSON.parse(line); } catch {
    throw new BridgeProtocolError("MALFORMED_JSON", "Request is not valid JSON");
  }
  const requestId = candidateRequestId(request);
  if (!exactKeys(request, ["protocolVersion", "requestId", "method", "params"])) {
    throw new BridgeProtocolError("INVALID_REQUEST", "Request fields are not allowed", requestId);
  }
  if (request.protocolVersion !== PROTOCOL_VERSION) {
    throw new BridgeProtocolError("INVALID_PROTOCOL", "Unsupported protocol version", requestId);
  }
  if (!validRequestId(request.requestId)) {
    throw new BridgeProtocolError("INVALID_REQUEST_ID", "requestId is invalid");
  }
  if (request.method !== "setTargetForm") {
    throw new BridgeProtocolError("UNKNOWN_METHOD", "Unsupported method", requestId);
  }
  if (!exactKeys(request.params, ["target", "animate"])) {
    throw new BridgeProtocolError("INVALID_PARAMS", "params must contain target and animate only", requestId);
  }
  if (request.params.target !== "gu" && request.params.target !== "feng") {
    throw new BridgeProtocolError("INVALID_TARGET", "target must be gu or feng", requestId);
  }
  if (typeof request.params.animate !== "boolean") {
    throw new BridgeProtocolError("INVALID_ANIMATE", "animate must be boolean", requestId);
  }
  return Object.freeze({
    requestId: request.requestId,
    target: request.params.target,
    animate: request.params.animate,
  });
}

export function successResponse(command, result) {
  if (result?.requestId !== command.requestId || typeof result.accepted !== "boolean"
      || (result.currentForm !== "gu" && result.currentForm !== "feng")
      || (result.targetForm !== "gu" && result.targetForm !== "feng")
      || typeof result.transitioning !== "boolean") {
    throw new BridgeProtocolError("INVALID_DISPATCH_RESULT", "Runtime result is invalid", command.requestId);
  }
  return Object.freeze({
    protocolVersion: PROTOCOL_VERSION, requestId: command.requestId, ok: true,
    result: Object.freeze({
      accepted: result.accepted, currentForm: result.currentForm,
      targetForm: result.targetForm, transitioning: result.transitioning,
    }),
  });
}

export function errorResponse(code, requestId = null) {
  const messages = Object.freeze({
    MESSAGE_TOO_LARGE: "Request exceeds the message limit",
    INVALID_FRAMING: "Expected one JSON object per line",
    MALFORMED_JSON: "Request is not valid JSON",
    INVALID_REQUEST: "Request fields are not allowed",
    INVALID_PROTOCOL: "Unsupported protocol version",
    INVALID_REQUEST_ID: "requestId is invalid",
    UNKNOWN_METHOD: "Unsupported method",
    INVALID_PARAMS: "params must contain target and animate only",
    INVALID_TARGET: "target must be gu or feng",
    INVALID_ANIMATE: "animate must be boolean",
    DUPLICATE_REQUEST_ID: "requestId was already used for another command",
    RUNTIME_TIMEOUT: "Runtime did not respond in time",
    RUNTIME_NOT_READY: "Pet runtime is not ready",
    DISPATCH_FAILED: "Pet runtime could not process the request",
    INVALID_DISPATCH_RESULT: "Pet runtime returned an invalid response",
  });
  const safeCode = Object.hasOwn(messages, code) ? code : "DISPATCH_FAILED";
  return Object.freeze({
    protocolVersion: PROTOCOL_VERSION,
    requestId: validRequestId(requestId) ? requestId : null,
    ok: false, error: Object.freeze({ code: safeCode, message: messages[safeCode] }),
  });
}

/** Identical Node/Python strategy: private user namespace under TMPDIR. */
export function defaultSocketPath({ tempDir = os.tmpdir(), uid = process.getuid() } = {}) {
  if (!Number.isInteger(uid) || uid < 0) throw new TypeError("uid must be a non-negative integer");
  const socketPath = path.join(tempDir, `${SOCKET_NAMESPACE}-${uid}`, "runtime.sock");
  if (Buffer.byteLength(socketPath, "utf8") > 100) {
    throw new RangeError("Unix socket path is too long for macOS");
  }
  return socketPath;
}
