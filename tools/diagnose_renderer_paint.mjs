/** Compare the actual baseline/fixed renderer under deterministic RAF skew.
 * A unit reproduction is not proof of the historical live exception.
 */
import fs from "node:fs";
import path from "node:path";
import { execFileSync } from "node:child_process";
import { rendererHarness, transitionState } from "../standalone-app/test-support/renderer-harness.mjs";

const root = path.resolve(import.meta.dirname, "..");
const output = process.argv[2];
if (!output) throw new Error("usage: node tools/diagnose_renderer_paint.mjs OUTPUT.json");
async function reproduce(source) {
  const h = rendererHarness({ source });
  h.setNow(100.25);
  await h.receive(transitionState());
  for (let i = 0; i < 7; i++) h.paint(100, 100.5);
  return { errors: h.errors, frame4Acknowledged: h.reports.some(e => e.transitionFrame === 4),
    pendingRafCallbacks: h.pendingCallbacks };
}
const old = execFileSync("git", ["show", "24b0df1:standalone-app/renderer.mjs"], { cwd: root, encoding: "utf8" });
const report = { evidenceKind: "DETERMINISTIC_ACTUAL_SOURCE_UNIT_REPRODUCTION_NOT_LIVE",
  baselineCommit: "24b0df1", historicalLiveRootCause: "NOT_PROVEN_WITHOUT_ERROR_TRACE",
  injectedOrdering: "RAF batch timestamp 100 precedes asynchronous state epoch 100.25",
  before: await reproduce(old), after: await reproduce(undefined) };
if (report.before.frame4Acknowledged || report.before.pendingRafCallbacks !== 0
    || !report.after.frame4Acknowledged || report.after.errors.length) throw new Error("reproduction mismatch");
fs.mkdirSync(path.dirname(output), { recursive: true });
fs.writeFileSync(output, JSON.stringify(report, null, 2) + "\n");
process.stdout.write(JSON.stringify(report, null, 2) + "\n");
