#!/usr/bin/env python3
"""Pure bridge-oriented scheduling decisions for Liang no Henshin."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, time, timedelta
from typing import Mapping, Any

if __package__:
    from .time_form_controller import ControllerError, expected_form_at, shanghai_time
else:
    from time_form_controller import ControllerError, expected_form_at, shanghai_time


TRANSITION_TIMES = (time(9, 0), time(12, 0), time(14, 0), time(18, 0))


@dataclass(frozen=True)
class SchedulerDecision:
    """One pure time-to-form decision with a strictly future wake target."""

    current_time: datetime
    expected_form: str
    next_transition: datetime
    should_send: bool


def next_transition(now: datetime) -> datetime:
    """Return the next strictly future node that changes the expected form."""

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
    """Return a non-negative Shanghai wall-clock duration."""

    current = shanghai_time(now)
    normalized_target = shanghai_time(target)
    return max(0.0, (normalized_target - current).total_seconds())


class FormScheduler:
    """Track only acknowledged form state; perform no transport or I/O."""

    def __init__(self, *, last_acknowledged_form: str | None = None) -> None:
        if last_acknowledged_form not in {None, "gu", "feng"}:
            raise ValueError("last_acknowledged_form must be gu, feng, or None")
        self._last_acknowledged_form = last_acknowledged_form
        self._reconcile_required = True

    @property
    def last_acknowledged_form(self) -> str | None:
        return self._last_acknowledged_form

    def require_reconcile(self) -> None:
        """Mark a new/unknown runtime session for one non-assumptive send."""

        self._reconcile_required = True

    def decide(self, now: datetime | None = None) -> SchedulerDecision:
        """Compute expected form and whether the caller should send it."""

        current = shanghai_time(now)
        expected = expected_form_at(current)
        should_send = (
            self._reconcile_required or expected != self._last_acknowledged_form
        )
        return SchedulerDecision(
            current_time=current,
            expected_form=expected,
            next_transition=next_transition(current),
            should_send=should_send,
        )

    def record_delivery(
        self, target: str, result: Mapping[str, Any] | None
    ) -> bool:
        """Acknowledge *target* only for an explicit accepted bridge result."""

        if target not in {"gu", "feng"}:
            raise ValueError("target must be gu or feng")
        accepted = isinstance(result, Mapping) and result.get("accepted") is True
        if accepted:
            self._last_acknowledged_form = target
            self._reconcile_required = False
        return accepted
