from __future__ import annotations

import os
import time
from datetime import datetime, timezone
from pathlib import Path

import pytest

from tools.time_form_scheduler import (
    FormScheduler,
    next_transition,
    seconds_until_transition,
)


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("2026-01-05T08:59:00", "gu"),
        ("2026-01-05T09:00:00", "feng"),
        ("2026-01-05T11:59:00", "feng"),
        ("2026-01-05T12:00:00", "gu"),
        ("2026-01-05T13:59:00", "gu"),
        ("2026-01-05T14:00:00", "feng"),
        ("2026-01-05T17:59:00", "feng"),
        ("2026-01-05T18:00:00", "gu"),
        ("2026-01-09T17:59:00", "feng"),
        ("2026-01-09T18:00:00", "gu"),
        ("2026-01-10T10:30:00", "gu"),
        ("2026-01-11T15:30:00", "gu"),
    ],
)
def test_schedule_boundaries(value: str, expected: str) -> None:
    decision = FormScheduler().decide(datetime.fromisoformat(value))
    assert decision.expected_form == expected


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("2026-01-05T08:59:00", "2026-01-05T09:00:00+08:00"),
        ("2026-01-05T09:00:00", "2026-01-05T12:00:00+08:00"),
        ("2026-01-05T12:00:00", "2026-01-05T14:00:00+08:00"),
        ("2026-01-05T14:00:00", "2026-01-05T18:00:00+08:00"),
        ("2026-01-05T18:00:00", "2026-01-06T09:00:00+08:00"),
        ("2026-01-09T18:00:00", "2026-01-12T09:00:00+08:00"),
        ("2026-01-10T10:30:00", "2026-01-12T09:00:00+08:00"),
        ("2026-01-11T15:30:00", "2026-01-12T09:00:00+08:00"),
    ],
)
def test_next_transition_is_strictly_future(value: str, expected: str) -> None:
    now = datetime.fromisoformat(value)
    target = next_transition(now)
    assert target.isoformat(timespec="seconds") == expected
    assert target > now.replace(tzinfo=target.tzinfo)


def test_startup_always_reconciles_even_with_persisted_ack() -> None:
    scheduler = FormScheduler(last_acknowledged_form="gu")
    assert scheduler.decide(datetime(2026, 1, 5, 8, 30)).should_send is True


@pytest.mark.parametrize(("form", "hour"), [("gu", 8), ("feng", 10)])
def test_acknowledged_form_becomes_no_op(form: str, hour: int) -> None:
    scheduler = FormScheduler()
    decision = scheduler.decide(datetime(2026, 1, 5, hour, 30))
    assert scheduler.record_delivery(form, {"accepted": True}) is True
    assert scheduler.decide(decision.current_time).should_send is False


def test_form_change_requests_delivery() -> None:
    scheduler = FormScheduler()
    scheduler.record_delivery("gu", {"accepted": True})
    assert scheduler.decide(datetime(2026, 1, 5, 9, 0)).should_send is True
    scheduler.record_delivery("feng", {"accepted": True})
    assert scheduler.decide(datetime(2026, 1, 5, 12, 0)).should_send is True


def test_failed_delivery_does_not_acknowledge() -> None:
    scheduler = FormScheduler()
    assert scheduler.record_delivery("feng", None) is False
    assert scheduler.record_delivery("feng", {"accepted": False}) is False
    assert scheduler.last_acknowledged_form is None
    assert scheduler.decide(datetime(2026, 1, 5, 10, 0)).should_send is True


def test_successful_delivery_updates_acknowledgment() -> None:
    scheduler = FormScheduler()
    assert scheduler.record_delivery("feng", {"accepted": True}) is True
    assert scheduler.last_acknowledged_form == "feng"


def test_runtime_session_invalidation_forces_reconcile() -> None:
    scheduler = FormScheduler()
    scheduler.record_delivery("feng", {"accepted": True})
    scheduler.require_reconcile()
    assert scheduler.decide(datetime(2026, 1, 5, 10, 0)).should_send is True


def test_timezone_is_shanghai_and_caller_timezone_does_not_change_rule() -> None:
    utc = datetime(2026, 1, 5, 1, 0, tzinfo=timezone.utc)
    decision = FormScheduler().decide(utc)
    assert decision.current_time.tzinfo is not None
    assert decision.current_time.tzinfo.key == "Asia/Shanghai"  # type: ignore[union-attr]
    assert decision.expected_form == "feng"


def test_seconds_until_transition_is_clamped() -> None:
    now = datetime(2026, 1, 5, 8, 59)
    target = next_transition(now)
    assert seconds_until_transition(now, target) == 60.0
    assert seconds_until_transition(target, target) == 0.0


def test_scheduler_has_no_filesystem_or_socket_side_effects(tmp_path: Path) -> None:
    before = set(tmp_path.iterdir())
    scheduler = FormScheduler()
    scheduler.decide(datetime(2026, 1, 5, 10, 0))
    scheduler.record_delivery("feng", {"accepted": True})
    assert set(tmp_path.iterdir()) == before
    source = Path(__file__).parents[1] / "tools" / "time_form_scheduler.py"
    text = source.read_text()
    assert "socket" not in text
    assert "Path(" not in text
    assert "open(" not in text
    assert "os.replace" not in text


def test_process_timezone_does_not_affect_naive_shanghai_contract(monkeypatch: pytest.MonkeyPatch) -> None:
    original = os.environ.get("TZ")
    monkeypatch.setenv("TZ", "America/Los_Angeles")
    if hasattr(time, "tzset"):
        time.tzset()
    try:
        assert FormScheduler().decide(datetime(2026, 1, 5, 9, 0)).expected_form == "feng"
    finally:
        if original is None:
            monkeypatch.delenv("TZ", raising=False)
        else:
            monkeypatch.setenv("TZ", original)
        if hasattr(time, "tzset"):
            time.tzset()
