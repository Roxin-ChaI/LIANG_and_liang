/** Asia/Shanghai schedule matching tools/time_form_scheduler.py. */
const formatter = new Intl.DateTimeFormat("en-CA", {
  timeZone: "Asia/Shanghai", year: "numeric", month: "2-digit", day: "2-digit",
  hour: "2-digit", minute: "2-digit", second: "2-digit", hourCycle: "h23",
});
const HOURS = [9, 12, 14, 18];

function parts(now) {
  if (!(now instanceof Date) || Number.isNaN(now.valueOf())) throw new TypeError("now must be a valid Date");
  const values = Object.fromEntries(formatter.formatToParts(now).filter((part) => part.type !== "literal")
    .map((part) => [part.type, Number(part.value)]));
  return { year: values.year, month: values.month, day: values.day,
    hour: values.hour, minute: values.minute, second: values.second };
}

function weekday(value) {
  return new Date(Date.UTC(value.year, value.month - 1, value.day)).getUTCDay();
}

export function expectedFormAt(now) {
  const value = parts(now);
  if ([0, 6].includes(weekday(value))) return "gu";
  const minutes = value.hour * 60 + value.minute;
  return (minutes >= 540 && minutes < 720) || (minutes >= 840 && minutes < 1080) ? "feng" : "gu";
}

export function nextTransition(now) {
  const value = parts(now);
  const day = Date.UTC(value.year, value.month - 1, value.day);
  for (let offset = 0; offset < 8; offset += 1) {
    const date = new Date(day + offset * 86_400_000);
    if ([0, 6].includes(date.getUTCDay())) continue;
    const ymd = `${date.getUTCFullYear()}-${String(date.getUTCMonth() + 1).padStart(2, "0")}-${String(date.getUTCDate()).padStart(2, "0")}`;
    for (const hour of HOURS) {
      const candidate = new Date(`${ymd}T${String(hour).padStart(2, "0")}:00:00+08:00`);
      if (candidate > now) return candidate;
    }
  }
  throw new Error("no future transition within eight days");
}

/** One wake timer, plus explicit resume/reconcile for sleep and clock changes. */
export function createFormScheduler({ now = () => new Date(), setTimer = setTimeout,
  clearTimer = clearTimeout, onTarget }) {
  if (typeof onTarget !== "function") throw new TypeError("onTarget is required");
  let timer = null;
  let active = true;
  let generation = 0;
  async function reconcile(reason = "startup") {
    if (!active) return null;
    const id = ++generation;
    if (timer !== null) clearTimer(timer);
    timer = null;
    const current = now();
    const target = expectedFormAt(current);
    await onTarget(target, { reason, currentTime: current });
    if (!active || id !== generation) return null;
    const next = nextTransition(now());
    timer = setTimer(() => { void reconcile("boundary"); }, Math.max(1, next.valueOf() - now().valueOf()));
    return Object.freeze({ expectedForm: target, nextTransition: next });
  }
  function stop() {
    active = false;
    ++generation;
    if (timer !== null) clearTimer(timer);
    timer = null;
  }
  return Object.freeze({ reconcile, stop });
}
