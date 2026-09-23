from __future__ import annotations

from pathlib import Path

import pytest

from tools import launch_temp_codex_once as subject


def test_isolated_environment_does_not_inherit_credentials(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "do-not-copy")
    monkeypatch.setenv("CODEX_AUTH_TOKEN", "do-not-copy")
    environment = subject.isolated_environment(tmp_path)
    assert "OPENAI_API_KEY" not in environment
    assert "CODEX_AUTH_TOKEN" not in environment
    assert environment["HOME"] == str(tmp_path / "home")
    assert environment["CODEX_HOME"] == str(tmp_path / "codex-home")
    assert environment["CODEX_ELECTRON_USER_DATA_PATH"] == str(tmp_path / "user-data")
    assert environment["TMPDIR"].startswith(str(tmp_path / "runtime/tmp"))


def test_second_launch_attempt_is_refused_before_verification(monkeypatch, tmp_path: Path) -> None:
    app = tmp_path / "ChatGPT.app"
    app.mkdir()
    (tmp_path / "launch-attempt.json").write_text("attempted")
    monkeypatch.setattr(subject, "TEMP_ROOT", tmp_path)
    monkeypatch.setattr(subject, "TEMP_APP", app)
    monkeypatch.setattr(subject, "verify_signed_temp_app", lambda *_args: (_ for _ in ()).throw(AssertionError("must not verify")))
    with pytest.raises(ValueError, match="already"):
        subject.launch_once(tmp_path, app)
