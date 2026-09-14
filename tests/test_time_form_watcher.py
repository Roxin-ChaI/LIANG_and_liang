from __future__ import annotations

import subprocess
import sys
import tempfile
import unittest
from datetime import datetime
from pathlib import Path

from tools.time_form_controller import REFRESH_INSTRUCTION
from tools.time_form_watcher import (
    WatchEvent,
    next_transition,
    seconds_until_transition,
    watch,
)

ROOT = Path(__file__).resolve().parents[1]
WATCHER = ROOT / "tools" / "time_form_watcher.py"


class NextTransitionTests(unittest.TestCase):
    def test_required_transition_cases(self) -> None:
        cases = {
            "2026-01-05T08:59:00": "2026-01-05T09:00:00+08:00",  # Monday
            "2026-01-05T09:00:00": "2026-01-05T12:00:00+08:00",
            "2026-01-05T11:59:00": "2026-01-05T12:00:00+08:00",
            "2026-01-05T12:00:00": "2026-01-05T14:00:00+08:00",
            "2026-01-05T14:00:00": "2026-01-05T18:00:00+08:00",
            "2026-01-05T18:00:00": "2026-01-06T09:00:00+08:00",
            "2026-01-09T18:00:00": "2026-01-12T09:00:00+08:00",  # Friday
            "2026-01-10T10:30:00": "2026-01-12T09:00:00+08:00",  # Saturday
            "2026-01-11T15:30:00": "2026-01-12T09:00:00+08:00",  # Sunday
        }
        for value, expected in cases.items():
            with self.subTest(value=value):
                actual = next_transition(datetime.fromisoformat(value))
                self.assertEqual(actual.isoformat(timespec="seconds"), expected)

    def test_seconds_until_transition_is_clamped(self) -> None:
        now = datetime.fromisoformat("2026-01-05T08:59:00")
        target = next_transition(now)
        self.assertEqual(seconds_until_transition(now, target), 60.0)
        self.assertEqual(seconds_until_transition(target, target), 0.0)
        self.assertEqual(seconds_until_transition(target, now), 0.0)


class FakeTime:
    def __init__(self, now: datetime, wake_times: list[datetime]) -> None:
        self.now = now
        self.wake_times = list(wake_times)
        self.sleep_calls: list[float] = []
        self.before_wake = None

    def clock(self) -> datetime:
        return self.now

    def sleep(self, seconds: float) -> None:
        self.sleep_calls.append(seconds)
        if self.before_wake is not None:
            self.before_wake()
        self.now = self.wake_times.pop(0)


class WatcherTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary_directory.name)
        self.gu = self.root / "gu.webp"
        self.feng = self.root / "feng.webp"
        self.active = self.root / "pet" / "spritesheet.webp"
        self.active.parent.mkdir()
        self.gu.write_bytes(b"approved-gu-atlas")
        self.feng.write_bytes(b"approved-feng-atlas")
        self.atlases = {"gu": self.gu, "feng": self.feng}

    def tearDown(self) -> None:
        self.temporary_directory.cleanup()

    def run_bounded(self, fake_time: FakeTime, wakeups: int = 1) -> list[WatchEvent]:
        events: list[WatchEvent] = []
        watch(
            atlases=self.atlases,
            active_atlas=self.active,
            clock=fake_time.clock,
            sleeper=fake_time.sleep,
            on_event=events.append,
            max_wakeups=wakeups,
        )
        return events

    def test_sleep_wake_after_crossing_one_node(self) -> None:
        self.active.write_bytes(self.gu.read_bytes())
        fake_time = FakeTime(
            datetime.fromisoformat("2026-01-05T08:59:00"),
            [datetime.fromisoformat("2026-01-05T10:00:00")],
        )
        events = self.run_bounded(fake_time)

        self.assertEqual(len(events), 2)
        self.assertEqual(fake_time.sleep_calls, [60.0])
        self.assertEqual(events[1].status.current_form, "feng")
        self.assertTrue(events[1].status.switched)
        self.assertEqual(
            events[1].next_transition.isoformat(timespec="seconds"),
            "2026-01-05T12:00:00+08:00",
        )

    def test_sleep_wake_after_crossing_multiple_nodes(self) -> None:
        self.active.write_bytes(self.gu.read_bytes())
        fake_time = FakeTime(
            datetime.fromisoformat("2026-01-05T08:59:00"),
            [datetime.fromisoformat("2026-01-05T15:00:00")],
        )
        events = self.run_bounded(fake_time)

        # Only startup and resume are reconciled; 09:00, 12:00 and 14:00 are
        # not replayed as historical events.
        self.assertEqual(len(events), 2)
        self.assertEqual(events[1].status.current_form, "feng")
        self.assertEqual(
            events[1].next_transition.isoformat(timespec="seconds"),
            "2026-01-05T18:00:00+08:00",
        )

    def test_no_op_when_atlas_is_already_correct_at_target(self) -> None:
        self.active.write_bytes(self.gu.read_bytes())
        fake_time = FakeTime(
            datetime.fromisoformat("2026-01-05T08:59:00"),
            [datetime.fromisoformat("2026-01-05T09:00:00")],
        )
        fake_time.before_wake = lambda: self.active.write_bytes(self.feng.read_bytes())
        events = self.run_bounded(fake_time)

        self.assertFalse(events[1].status.switched)
        self.assertFalse(events[1].status.refresh_required)
        self.assertEqual(events[1].status.current_form, "feng")

    def test_startup_controller_integration_and_refresh_action(self) -> None:
        self.active.write_bytes(self.gu.read_bytes())
        fake_time = FakeTime(datetime.fromisoformat("2026-01-05T09:00:00"), [])
        events = self.run_bounded(fake_time, wakeups=0)

        self.assertEqual(len(events), 1)
        self.assertEqual(events[0].previous_form, "gu")
        self.assertEqual(events[0].status.current_form, "feng")
        self.assertTrue(events[0].status.refresh_required)
        self.assertEqual(events[0].status.refresh_instruction, REFRESH_INSTRUCTION)

    def test_cli_once_smoke(self) -> None:
        self.active.write_bytes(self.gu.read_bytes())
        completed = subprocess.run(
            [
                sys.executable,
                str(WATCHER),
                "--once",
                "--at",
                "2026-01-05T08:30:00",
                "--gu-atlas",
                str(self.gu),
                "--feng-atlas",
                str(self.feng),
                "--active-atlas",
                str(self.active),
            ],
            check=True,
            capture_output=True,
            text=True,
        )
        self.assertIn("current_form=gu", completed.stdout)
        self.assertIn("expected_form=gu", completed.stdout)
        self.assertIn("switched=false", completed.stdout)
        self.assertIn("refresh_required=false", completed.stdout)
        self.assertIn(
            "next_transition=2026-01-05T09:00:00+08:00", completed.stdout
        )

    def test_cli_once_reports_switch_and_manual_refresh(self) -> None:
        self.active.write_bytes(self.gu.read_bytes())
        completed = subprocess.run(
            [
                sys.executable,
                str(WATCHER),
                "--once",
                "--at",
                "2026-01-05T09:00:00",
                "--gu-atlas",
                str(self.gu),
                "--feng-atlas",
                str(self.feng),
                "--active-atlas",
                str(self.active),
            ],
            check=True,
            capture_output=True,
            text=True,
        )
        self.assertIn("switched=true", completed.stdout)
        self.assertIn("from=gu", completed.stdout)
        self.assertIn("to=feng", completed.stdout)
        self.assertIn("refresh_required=true", completed.stdout)
        self.assertIn(f'action="{REFRESH_INSTRUCTION}"', completed.stdout)
        self.assertIn(
            "next_transition=2026-01-05T12:00:00+08:00", completed.stdout
        )


if __name__ == "__main__":
    unittest.main()
