#!/usr/bin/env python3
"""Run the Shanghai Gu/Feng schedule through the local runtime bridge."""

from __future__ import annotations

import argparse
import stat
import time as time_module
import uuid
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Mapping

if __package__:
    from .pet_runtime_client import (
        PetRuntimeClientError,
        default_socket_path,
        set_target_form,
    )
    from .time_form_controller import parse_time, shanghai_time
    from .time_form_scheduler import (
        FormScheduler,
        SchedulerDecision,
        seconds_until_transition,
    )
else:
    from pet_runtime_client import (
        PetRuntimeClientError,
        default_socket_path,
        set_target_form,
    )
    from time_form_controller import parse_time, shanghai_time
    from time_form_scheduler import (
        FormScheduler,
        SchedulerDecision,
        seconds_until_transition,
    )


RETRY_DELAYS = (1.0, 2.0, 4.0, 8.0, 15.0, 30.0, 60.0)
_UNSEEN = object()

Clock = Callable[[], datetime]
Sleeper = Callable[[float], None]
BridgeClient = Callable[..., Mapping[str, Any]]
SessionProbe = Callable[[], object | None]
Emitter = Callable[[str], None]


@dataclass(frozen=True)
class WatchEvent:
    """One scheduler observation and optional bridge delivery result."""

    decision: SchedulerDecision
    request_id: str | None
    animate: bool | None
    accepted: bool
    transitioning: bool
    error_code: str | None
    retry_after: float | None
    sent: bool


def emit_line(message: str) -> None:
    print(message, flush=True)


def current_time() -> datetime:
    return shanghai_time()


def runtime_session_identity(socket_path: Path | None = None) -> object | None:
    """Return a read-only identity for the current bridge socket generation."""

    path = socket_path or default_socket_path()
    try:
        details = path.stat()
    except FileNotFoundError:
        return None
    if not stat.S_ISSOCK(details.st_mode):
        return None
    return (details.st_dev, details.st_ino, details.st_ctime_ns)


class BridgeWatcher:
    """Session-aware delivery state layered over the pure scheduler."""

    def __init__(
        self,
        *,
        client: BridgeClient = set_target_form,
        session_probe: SessionProbe = runtime_session_identity,
        scheduler: FormScheduler | None = None,
        request_id_factory: Callable[[], str] = lambda: str(uuid.uuid4()),
    ) -> None:
        self.client = client
        self.session_probe = session_probe
        self.scheduler = scheduler or FormScheduler()
        self.request_id_factory = request_id_factory
        self._session: object = _UNSEEN
        self._retry_index = 0

    def _failed(self) -> float:
        delay = RETRY_DELAYS[min(self._retry_index, len(RETRY_DELAYS) - 1)]
        self._retry_index = min(self._retry_index + 1, len(RETRY_DELAYS) - 1)
        self._session = None
        self.scheduler.require_reconcile()
        return delay

    def attempt(self, now: datetime | None = None) -> WatchEvent:
        """Reconcile once; errors become bounded-retry events, not crashes."""

        session = self.session_probe()
        session_changed = self._session is _UNSEEN or session != self._session
        if session_changed:
            self.scheduler.require_reconcile()
        decision = self.scheduler.decide(now)
        if not decision.should_send:
            return WatchEvent(
                decision, None, None, False, False, None, None, False
            )

        animate = not session_changed and self._session is not None
        request_id = self.request_id_factory()
        try:
            result = self.client(
                decision.expected_form,
                animate=animate,
                request_id=request_id,
            )
            accepted = self.scheduler.record_delivery(
                decision.expected_form, result
            )
            if not accepted:
                return WatchEvent(
                    decision,
                    request_id,
                    animate,
                    False,
                    bool(result.get("transitioning", False)),
                    "NOT_ACCEPTED",
                    self._failed(),
                    True,
                )
            self._session = self.session_probe()
            self._retry_index = 0
            return WatchEvent(
                decision,
                request_id,
                animate,
                True,
                bool(result.get("transitioning", False)),
                None,
                None,
                True,
            )
        except (PetRuntimeClientError, OSError) as error:
            return WatchEvent(
                decision,
                request_id,
                animate,
                False,
                False,
                getattr(error, "code", "BRIDGE_ERROR"),
                self._failed(),
                True,
            )


def emit_event(event: WatchEvent, emit: Emitter = emit_line) -> None:
    decision = event.decision
    emit(f"current_time={decision.current_time.isoformat(timespec='seconds')}")
    emit(f"expected_form={decision.expected_form}")
    emit(f"request_id={event.request_id or 'none'}")
    emit(f"sent={str(event.sent).lower()}")
    if event.animate is not None:
        emit(f"animate={str(event.animate).lower()}")
    emit(f"accepted={str(event.accepted).lower()}")
    emit(f"transitioning={str(event.transitioning).lower()}")
    if event.error_code is not None:
        emit(f"error_code={event.error_code}")
    if event.retry_after is not None:
        emit(f"retry_after={event.retry_after:g}")
    emit(
        f"next_transition={decision.next_transition.isoformat(timespec='seconds')}"
    )


def watch(
    *,
    clock: Clock = current_time,
    sleeper: Sleeper = time_module.sleep,
    bridge: BridgeWatcher | None = None,
    on_event: Callable[[WatchEvent], None] = emit_event,
    max_iterations: int | None = None,
) -> None:
    """Reconcile immediately, then sleep to retry or the next real node."""

    if max_iterations is not None and max_iterations < 1:
        raise ValueError("max_iterations must be positive or None")
    runtime = bridge or BridgeWatcher()
    iterations = 0
    while max_iterations is None or iterations < max_iterations:
        event = runtime.attempt(clock())
        on_event(event)
        iterations += 1
        if max_iterations is not None and iterations >= max_iterations:
            return

        observed = shanghai_time(clock())
        until_node = seconds_until_transition(
            observed, event.decision.next_transition
        )
        delay = (
            min(event.retry_after, until_node)
            if event.retry_after is not None and until_node > 0
            else event.retry_after
            if event.retry_after is not None
            else until_node
        )
        sleeper(max(0.0, delay))


def dry_run(now: datetime | None = None, emit: Emitter = emit_line) -> None:
    """Print one pure decision without probing or connecting to the bridge."""

    decision = FormScheduler().decide(now)
    emit(f"current_time={decision.current_time.isoformat(timespec='seconds')}")
    emit(f"expected_form={decision.expected_form}")
    emit(
        f"next_transition={decision.next_transition.isoformat(timespec='seconds')}"
    )
    emit("dry_run=true")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Watch Shanghai peak windows through the Liang runtime bridge."
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="print the current decision without connecting or writing",
    )
    parser.add_argument(
        "--at",
        type=parse_time,
        help="ISO-8601 override; valid only with --dry-run",
    )
    parser.add_argument("--socket-path", type=Path, default=default_socket_path())
    args = parser.parse_args()
    if args.at is not None and not args.dry_run:
        parser.error("--at requires --dry-run")
    if args.dry_run:
        dry_run(args.at)
        return 0

    client = lambda target, **kwargs: set_target_form(  # noqa: E731
        target, socket_path=args.socket_path, **kwargs
    )
    probe = lambda: runtime_session_identity(args.socket_path)  # noqa: E731
    try:
        watch(bridge=BridgeWatcher(client=client, session_probe=probe))
    except KeyboardInterrupt:
        print("stopped=true", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
