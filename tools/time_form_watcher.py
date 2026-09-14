#!/usr/bin/env python3
"""Wait for Liang no Henshin peak/off-peak transitions in the foreground."""

from __future__ import annotations

import argparse
import time as time_module
from dataclasses import dataclass
from datetime import datetime, time, timedelta
from pathlib import Path
from typing import Callable, Mapping

if __package__:
    from .time_form_controller import (
        DEFAULT_ACTIVE_ATLAS,
        DEFAULT_ATLASES,
        REFRESH_INSTRUCTION,
        ControllerError,
        ControllerStatus,
        identify_form,
        parse_time,
        run_controller,
        sha256,
        shanghai_time,
    )
else:
    from time_form_controller import (
        DEFAULT_ACTIVE_ATLAS,
        DEFAULT_ATLASES,
        REFRESH_INSTRUCTION,
        ControllerError,
        ControllerStatus,
        identify_form,
        parse_time,
        run_controller,
        sha256,
        shanghai_time,
    )

TRANSITION_TIMES = (time(9, 0), time(12, 0), time(14, 0), time(18, 0))

Clock = Callable[[], datetime]
Sleeper = Callable[[float], None]
Controller = Callable[..., ControllerStatus]
Emitter = Callable[[str], None]


def emit_line(message: str) -> None:
    """Print watcher status immediately before the next potentially long sleep."""

    print(message, flush=True)


@dataclass(frozen=True)
class WatchEvent:
    """One controller reconciliation and its next future transition."""

    status: ControllerStatus
    previous_form: str
    next_transition: datetime


def next_transition(now: datetime) -> datetime:
    """Return the next strictly future node that changes gu/feng form."""

    current = shanghai_time(now)
    for day_offset in range(8):
        candidate_date = current.date() + timedelta(days=day_offset)
        if candidate_date.weekday() >= 5:
            continue
        for transition_time in TRANSITION_TIMES:
            candidate = datetime.combine(
                candidate_date, transition_time, tzinfo=current.tzinfo
            )
            if candidate > current:
                return candidate
    raise ControllerError("unable to find a transition in the next eight days")


def seconds_until_transition(now: datetime, target: datetime) -> float:
    """Return a non-negative sleep duration using Shanghai wall-clock time."""

    current = shanghai_time(now)
    normalized_target = shanghai_time(target)
    return max(0.0, (normalized_target - current).total_seconds())


def _source_hashes(atlases: Mapping[str, Path]) -> dict[str, str]:
    """Read the two approved source hashes for pre-controller reporting."""

    return {form: sha256(Path(atlases[form])) for form in ("gu", "feng")}


def reconcile(
    now: datetime,
    *,
    atlases: Mapping[str, Path],
    active_atlas: Path,
    controller: Controller = run_controller,
) -> WatchEvent:
    """Run the controller once and describe the resulting scheduled state."""

    current = shanghai_time(now)
    previous_form = identify_form(active_atlas, _source_hashes(atlases))
    status = controller(now=current, atlases=atlases, active_atlas=active_atlas)
    return WatchEvent(
        status=status,
        previous_form=previous_form,
        next_transition=next_transition(current),
    )


def emit_event(event: WatchEvent, emit: Emitter = emit_line) -> None:
    """Write one watcher event in a stable line-oriented format."""

    status = event.status
    emit(f"current_time={status.current_time}")
    emit(f"current_form={status.current_form}")
    emit(f"expected_form={status.expected_form}")
    emit(f"switched={str(status.switched).lower()}")
    if status.switched:
        emit(f"from={event.previous_form}")
        emit(f"to={status.current_form}")
    emit(f"refresh_required={str(status.refresh_required).lower()}")
    if status.refresh_required:
        emit(f'action="{REFRESH_INSTRUCTION}"')
    emit(f"next_transition={event.next_transition.isoformat(timespec='seconds')}")


def current_time() -> datetime:
    """Read the current time in Asia/Shanghai."""

    return shanghai_time()


def watch(
    *,
    atlases: Mapping[str, Path] = DEFAULT_ATLASES,
    active_atlas: Path = DEFAULT_ACTIVE_ATLAS,
    clock: Clock = current_time,
    sleeper: Sleeper = time_module.sleep,
    controller: Controller = run_controller,
    on_event: Callable[[WatchEvent], None] = emit_event,
    max_wakeups: int | None = None,
) -> None:
    """Reconcile now, then sleep directly to each future transition.

    ``max_wakeups`` exists for deterministic tests. ``None`` runs forever and
    ``0`` performs only the required startup reconciliation.
    """

    if max_wakeups is not None and max_wakeups < 0:
        raise ValueError("max_wakeups must be non-negative or None")

    event = reconcile(
        clock(), atlases=atlases, active_atlas=active_atlas, controller=controller
    )
    on_event(event)
    wakeups = 0

    while max_wakeups is None or wakeups < max_wakeups:
        target = event.next_transition

        # A sleep can return early. Conversely, macOS can resume after one or
        # several missed nodes. In both cases, always read the clock again.
        while True:
            now = clock()
            remaining = seconds_until_transition(now, target)
            if remaining > 0:
                sleeper(remaining)
            resumed_at = shanghai_time(clock())
            if resumed_at >= target:
                break

        # Reconcile once for the actual resume time. Historical nodes are not
        # replayed; next_transition() starts strictly after this observation.
        event = reconcile(
            resumed_at,
            atlases=atlases,
            active_atlas=active_atlas,
            controller=controller,
        )
        on_event(event)
        wakeups += 1


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Watch Shanghai peak windows and switch Liang no Henshin."
    )
    parser.add_argument(
        "--once",
        action="store_true",
        help="reconcile once, print the next transition, and exit",
    )
    parser.add_argument(
        "--at",
        type=parse_time,
        help="ISO-8601 time override; valid only with --once",
    )
    parser.add_argument("--gu-atlas", type=Path, default=DEFAULT_ATLASES["gu"])
    parser.add_argument("--feng-atlas", type=Path, default=DEFAULT_ATLASES["feng"])
    parser.add_argument("--active-atlas", type=Path, default=DEFAULT_ACTIVE_ATLAS)
    args = parser.parse_args()
    if args.at is not None and not args.once:
        parser.error("--at requires --once")

    clock = (lambda: args.at) if args.at is not None else current_time
    try:
        watch(
            atlases={"gu": args.gu_atlas, "feng": args.feng_atlas},
            active_atlas=args.active_atlas,
            clock=clock,
            max_wakeups=0 if args.once else None,
        )
    except KeyboardInterrupt:
        print("stopped=true", flush=True)
    except (ControllerError, OSError) as exc:
        raise SystemExit(f"watcher error: {exc}") from exc


if __name__ == "__main__":
    main()
