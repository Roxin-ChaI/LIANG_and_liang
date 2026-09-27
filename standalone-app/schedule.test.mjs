import assert from "node:assert/strict";
import test from "node:test";
import { createFormScheduler, expectedFormAt, nextTransition } from "./schedule.mjs";

const shanghai = (value) => new Date(`${value}+08:00`);

test("Beijing peak boundaries match the existing Python scheduler", () => {
  for (const [time, expected, next] of [
    ["2026-09-14T08:59:00", "gu", "2026-09-14T09:00:00"],
    ["2026-09-14T09:00:00", "feng", "2026-09-14T12:00:00"],
    ["2026-09-14T11:59:00", "feng", "2026-09-14T12:00:00"],
    ["2026-09-14T12:00:00", "gu", "2026-09-14T14:00:00"],
    ["2026-09-14T14:00:00", "feng", "2026-09-14T18:00:00"],
    ["2026-09-14T18:00:00", "gu", "2026-09-15T09:00:00"],
    ["2026-09-18T18:00:00", "gu", "2026-09-21T09:00:00"],
    ["2026-09-19T12:00:00", "gu", "2026-09-21T09:00:00"],
    ["2026-09-20T12:00:00", "gu", "2026-09-21T09:00:00"],
  ]) {
    assert.equal(expectedFormAt(shanghai(time)), expected, time);
    assert.equal(nextTransition(shanghai(time)).valueOf(), shanghai(next).valueOf(), time);
  }
});

test("sleep/wake skips history and reconciles only the current form", async () => {
  let current = shanghai("2026-09-14T08:59:00");
  const calls = [];
  const timers = [];
  const scheduler = createFormScheduler({ now: () => current,
    setTimer: (callback, delay) => { timers.push({ callback, delay }); return timers.length; },
    clearTimer: () => {}, onTarget: async (target, metadata) => calls.push([target, metadata.reason]),
  });
  await scheduler.reconcile();
  assert.deepEqual(calls, [["gu", "startup"]]);
  assert.equal(timers.at(-1).delay, 60_000);
  current = shanghai("2026-09-14T14:01:00");
  await scheduler.reconcile("resume");
  assert.deepEqual(calls.at(-1), ["feng", "resume"]);
  assert.equal(timers.at(-1).delay, 60_000);
  scheduler.stop();
});

test("exact boundary fires once and the next target is strictly future", async () => {
  let current = shanghai("2026-09-14T08:59:59");
  const calls = [];
  let timer;
  const scheduler = createFormScheduler({ now: () => current,
    setTimer: (callback, delay) => { timer = { callback, delay }; return timer; },
    clearTimer: () => {}, onTarget: async (form) => calls.push(form),
  });
  await scheduler.reconcile("startup");
  assert.equal(timer.delay, 1000);
  current = shanghai("2026-09-14T09:00:00");
  timer.callback();
  await new Promise((resolve) => setImmediate(resolve));
  assert.deepEqual(calls, ["gu", "feng"]);
  assert.equal(nextTransition(current).valueOf(), shanghai("2026-09-14T12:00:00").valueOf());
  scheduler.stop();
});

test("clock-check corrects forward jumps without replaying missed nodes", async () => {
  let current = shanghai("2026-09-14T09:01:00");
  const calls = [];
  let timer;
  const scheduler = createFormScheduler({ now: () => current,
    setTimer: (callback, delay) => { timer = { callback, delay }; return timer; },
    clearTimer: () => {}, onTarget: async (form) => calls.push(form),
  });
  await scheduler.reconcile("startup");
  assert.equal(timer.delay, 60_000);
  current = shanghai("2026-09-14T18:01:00");
  timer.callback();
  await new Promise((resolve) => setImmediate(resolve));
  assert.deepEqual(calls, ["feng", "gu"]);
  assert.equal(nextTransition(current).valueOf(), shanghai("2026-09-15T09:00:00").valueOf());
  scheduler.stop();
});

test("concurrent reconcile delivers the newest clock decision last", async () => {
  let current = shanghai("2026-09-14T08:59:00");
  const calls = [];
  let releaseOld;
  const scheduler = createFormScheduler({ now: () => current,
    setTimer: () => 1, clearTimer: () => {},
    onTarget: async (form) => {
      calls.push(form);
      if (form === "gu") await new Promise((resolve) => { releaseOld = resolve; });
    },
  });
  const first = scheduler.reconcile("startup");
  await new Promise((resolve) => setImmediate(resolve));
  current = shanghai("2026-09-14T09:00:00");
  const second = scheduler.reconcile("resume");
  releaseOld();
  assert.equal(await first, null);
  assert.equal((await second).expectedForm, "feng");
  assert.deepEqual(calls, ["gu", "feng"]);
  scheduler.stop();
});
