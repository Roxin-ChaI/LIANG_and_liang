import assert from "node:assert/strict";
import test from "node:test";
import { createPetEventAdapter } from "./events.mjs";

test("one typed interface accepts work, form and interaction events", () => {
  const calls = [];
  const adapter = createPetEventAdapter({
    updateUnderlyingState: (value) => calls.push(["work", value]),
    requestTargetForm: (form, options) => calls.push(["form", form, options.animate]),
    updateInteraction: (kind, value) => calls.push(["interaction", kind, value]),
  });
  adapter.dispatch({ type: "work-state", state: "running" });
  adapter.dispatch({ type: "target-form", form: "feng" });
  adapter.dispatch({ type: "interaction", kind: "hover", value: true });
  assert.deepEqual(calls, [["work", "running"], ["form", "feng", true], ["interaction", "hover", true]]);
  assert.throws(() => adapter.dispatch({ type: "work-state", state: "secret" }));
  assert.throws(() => adapter.dispatch({ type: "target-form", form: "other" }));
});
