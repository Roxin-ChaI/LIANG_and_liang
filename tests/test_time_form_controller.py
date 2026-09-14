from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest import mock

from tools.time_form_controller import (
    REFRESH_INSTRUCTION,
    ControllerError,
    expected_form_at,
    run_controller,
    sha256,
)

ROOT = Path(__file__).resolve().parents[1]
CONTROLLER = ROOT / "tools" / "time_form_controller.py"


class ScheduleBoundaryTests(unittest.TestCase):
    def test_required_boundaries(self) -> None:
        cases = {
            "2026-01-05T08:59:00": "gu",  # Monday
            "2026-01-05T09:00:00": "feng",
            "2026-01-05T11:59:00": "feng",
            "2026-01-05T12:00:00": "gu",
            "2026-01-05T13:59:00": "gu",
            "2026-01-05T14:00:00": "feng",
            "2026-01-05T17:59:00": "feng",
            "2026-01-05T18:00:00": "gu",
            "2026-01-09T17:59:00": "feng",  # Friday
            "2026-01-09T18:00:00": "gu",
            "2026-01-10T10:30:00": "gu",  # Saturday
            "2026-01-11T15:30:00": "gu",  # Sunday
        }
        for value, expected in cases.items():
            with self.subTest(value=value):
                self.assertEqual(expected_form_at(datetime.fromisoformat(value)), expected)

    def test_aware_time_is_converted_to_shanghai(self) -> None:
        # Monday 01:00 UTC is Monday 09:00 in Shanghai.
        value = datetime(2026, 1, 5, 1, 0, tzinfo=timezone.utc)
        self.assertEqual(expected_form_at(value), "feng")


class ControllerTests(unittest.TestCase):
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

    def test_correct_form_performs_no_write(self) -> None:
        self.active.write_bytes(self.gu.read_bytes())
        before_stat = self.active.stat()

        with mock.patch("tools.time_form_controller.atomic_replace") as replace:
            status = run_controller(
                now=datetime(2026, 1, 5, 8, 59),
                atlases=self.atlases,
                active_atlas=self.active,
            )

        replace.assert_not_called()
        self.assertEqual(self.active.stat().st_ino, before_stat.st_ino)
        self.assertFalse(status.switched)
        self.assertFalse(status.refresh_required)
        self.assertIsNone(status.refresh_instruction)
        self.assertEqual(status.current_form, "gu")

    def test_switches_atomically_and_verifies_final_form(self) -> None:
        self.active.write_bytes(self.gu.read_bytes())
        old_inode = self.active.stat().st_ino
        pet_json = self.active.parent / "pet.json"
        config = self.root / "config.toml"
        pet_json.write_bytes(b'{"id":"liang-no-henshin"}\n')
        config.write_bytes(b'selected-avatar-id = "custom:liang-no-henshin"\n')

        status = run_controller(
            now=datetime(2026, 1, 5, 9, 0),
            atlases=self.atlases,
            active_atlas=self.active,
        )

        self.assertNotEqual(self.active.stat().st_ino, old_inode)
        self.assertEqual(self.active.read_bytes(), self.feng.read_bytes())
        self.assertEqual(sha256(self.active), sha256(self.feng))
        self.assertEqual(pet_json.read_bytes(), b'{"id":"liang-no-henshin"}\n')
        self.assertEqual(
            config.read_bytes(),
            b'selected-avatar-id = "custom:liang-no-henshin"\n',
        )
        self.assertTrue(status.switched)
        self.assertTrue(status.refresh_required)
        self.assertEqual(status.refresh_instruction, REFRESH_INSTRUCTION)
        self.assertEqual(status.current_form, "feng")

    def test_unknown_active_atlas_is_replaced(self) -> None:
        self.active.write_bytes(b"unknown-atlas")
        status = run_controller(
            now=datetime(2026, 1, 10, 12, 0),
            atlases=self.atlases,
            active_atlas=self.active,
        )
        self.assertTrue(status.switched)
        self.assertEqual(status.current_form, "gu")
        self.assertEqual(self.active.read_bytes(), self.gu.read_bytes())

    def test_missing_active_directory_is_rejected(self) -> None:
        missing = self.root / "missing" / "spritesheet.webp"
        with self.assertRaisesRegex(ControllerError, "active pet directory not found"):
            run_controller(
                now=datetime(2026, 1, 5, 9, 0),
                atlases=self.atlases,
                active_atlas=missing,
            )

    def test_identical_source_hashes_are_rejected(self) -> None:
        self.feng.write_bytes(self.gu.read_bytes())
        with self.assertRaisesRegex(ControllerError, "same SHA256"):
            run_controller(
                now=datetime(2026, 1, 5, 9, 0),
                atlases=self.atlases,
                active_atlas=self.active,
            )

    def test_cli_outputs_required_status_fields(self) -> None:
        self.active.write_bytes(self.gu.read_bytes())
        completed = subprocess.run(
            [
                sys.executable,
                str(CONTROLLER),
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
        payload = json.loads(completed.stdout)
        self.assertEqual(
            set(payload),
            {
                "current_time",
                "expected_form",
                "current_form",
                "switched",
                "refresh_required",
                "refresh_instruction",
            },
        )
        self.assertEqual(payload["expected_form"], "feng")
        self.assertEqual(payload["current_form"], "feng")
        self.assertTrue(payload["switched"])
        self.assertEqual(payload["refresh_instruction"], REFRESH_INSTRUCTION)


if __name__ == "__main__":
    unittest.main()
