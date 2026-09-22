from __future__ import annotations

import hashlib
import importlib.util
import plistlib
import json
import struct
import sys
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / "tools"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


validator = load_module(
    "validate_clean_codex_reference_test_module", TOOLS / "validate_clean_codex_reference.py"
)
finder = load_module(
    "find_clean_codex_reference_test_module", TOOLS / "find_clean_codex_reference.py"
)


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def make_asar(payload: bytes = b"clean official archive") -> tuple[bytes, str]:
    encoded = json.dumps({"files": {}}, separators=(",", ":")).encode()
    aligned = (4 + len(encoded) + 1 + 3) & ~3
    header_size = 4 + aligned
    padding = aligned - (4 + len(encoded) + 1)
    archive = (
        struct.pack("<II", 4, header_size)
        + struct.pack("<II", aligned, len(encoded))
        + encoded
        + b"\0"
        + (b"\0" * padding)
        + payload
    )
    return archive, sha(encoded)


class FakeRunner:
    def __init__(self) -> None:
        self.commands: list[tuple[str, ...]] = []
        self.signature_ok = True
        self.gatekeeper_ok = True
        self.team_id = validator.PHASE7A_CONFIRMED_TEAM_ID
        self.entitlements = "valid"
        self.nested_failures: set[str] = set()
        self.on_run = None

    def result(
        self,
        argv: tuple[str, ...],
        returncode: int = 0,
        stdout: bytes = b"",
        stderr: bytes = b"",
        available: bool = True,
    ):
        return validator.CommandResult(argv, returncode, stdout, stderr, available)

    def run(self, argv):
        command = tuple(str(value) for value in argv)
        self.commands.append(command)
        if self.on_run is not None:
            self.on_run(command)
        if command[0] == "lipo":
            return self.result(command, stdout=b"arm64\n")
        if command[:3] == ("codesign", "-dv", "--verbose=4"):
            return self.result(
                command,
                stderr=(
                    b"Identifier=com.openai.codex\n"
                    b"CodeDirectory v=20500 flags=0x10000(runtime)\n"
                    + f"TeamIdentifier={self.team_id}\n".encode()
                    + b"Authority=Apple Distribution: OpenAI, L.L.C.\n"
                    b"Authority=Apple Worldwide Developer Relations Certification Authority\n"
                    b"Notarization Ticket=stapled\n"
                ),
            )
        if command[:4] == ("codesign", "--verify", "--deep", "--strict"):
            return self.result(
                command,
                returncode=0 if self.signature_ok else 1,
                stderr=b"" if self.signature_ok else b"invalid signature",
            )
        if command[:3] == ("codesign", "--verify", "--strict"):
            failed = command[-1] in self.nested_failures
            return self.result(
                command,
                returncode=int(failed),
                stderr=b"invalid nested signature" if failed else b"",
            )
        if command[:4] == ("codesign", "--display", "--entitlements", "-"):
            if self.entitlements == "valid":
                return self.result(
                    command,
                    stdout=plistlib.dumps(
                        {
                            "com.apple.application-identifier": (
                                validator.PHASE7A_CONFIRMED_TEAM_ID + ".com.openai.codex"
                            ),
                            "com.apple.security.cs.allow-jit": True,
                        }
                    ),
                )
            if self.entitlements == "malformed":
                return self.result(command, stderr=b"warning: invalid entitlements blob")
            return self.result(command)
        if command[0] == "spctl":
            return self.result(
                command,
                returncode=0 if self.gatekeeper_ok else 1,
                stderr=b"accepted" if self.gatekeeper_ok else b"rejected",
            )
        return self.result(command)


def make_app(
    root: Path,
    *,
    name: str = "ChatGPT.app",
    bundle_id: str = "com.openai.codex",
    integrity_matches: bool = True,
) -> Path:
    app = root / name
    contents = app / "Contents"
    resources = contents / "Resources"
    executable_dir = contents / "MacOS"
    signature_dir = contents / "_CodeSignature"
    resources.mkdir(parents=True)
    executable_dir.mkdir()
    signature_dir.mkdir()
    archive, header_hash = make_asar()
    (resources / "app.asar").write_bytes(archive)
    (executable_dir / "ChatGPT").write_bytes(b"clean executable")
    (signature_dir / "CodeResources").write_bytes(b"sealed resources")
    expected = header_hash if integrity_matches else "0" * 64
    with (contents / "Info.plist").open("wb") as handle:
        plistlib.dump(
            {
                "CFBundleIdentifier": bundle_id,
                "CFBundleShortVersionString": "26.915.31945",
                "CFBundleVersion": "9922",
                "CFBundleExecutable": "ChatGPT",
                "ElectronAsarIntegrity": {
                    "Resources/app.asar": {"algorithm": "SHA256", "hash": expected}
                },
            },
            handle,
        )
    return app


def validate(app: Path, runner: FakeRunner, *, nested_components=()):
    return validator.validate_candidate(
        app,
        runner=runner,
        nested_components=nested_components,
        installed_app=app.parent / "installed/ChatGPT.app",
    )


def test_clean_candidate_passes_every_gate(tmp_path: Path) -> None:
    app = make_app(tmp_path)
    result = validate(app, FakeRunner())
    assert result["classification"] == "CLEAN_REFERENCE_PASS"
    assert result["bundleIdentifier"] == "com.openai.codex"
    assert result["architectures"] == ["arm64"]
    assert result["codesign"]["returncode"] == 0
    assert result["entitlements"]["status"] == "VALID_XML"
    assert result["asarIntegrity"]["status"] == "ASAR_INTEGRITY_MATCH"
    assert result["asarIntegrity"]["scope"] == "raw-json-header"
    assert result["appAsarSha256"] == sha((app / "Contents/Resources/app.asar").read_bytes())
    assert result["signatureIdentity"]["teamIdentifier"] == "2DC432GLL2"
    assert result["signatureIdentity"]["hardenedRuntime"] is True
    assert result["zeroMutation"] is True


def test_signature_failure_is_rejected(tmp_path: Path) -> None:
    app = make_app(tmp_path)
    runner = FakeRunner()
    runner.signature_ok = False
    assert validate(app, runner)["classification"] == "REJECT_SIGNATURE"


def test_nested_signature_failure_is_rejected(tmp_path: Path) -> None:
    app = make_app(tmp_path)
    nested = app / "Contents/Frameworks/Codex Helper.app"
    nested.mkdir(parents=True)
    runner = FakeRunner()
    runner.nested_failures.add(str(nested))
    result = validate(app, runner, nested_components=[nested])
    assert result["classification"] == "REJECT_SIGNATURE"
    assert result["nestedSignatures"]["firstFailingComponent"] == str(nested)


def test_non_macho_cross_platform_node_is_not_a_nested_signing_target(tmp_path: Path) -> None:
    app = make_app(tmp_path)
    foreign = app / "Contents/Resources/prebuilds/linux-x64/addon.node"
    foreign.parent.mkdir(parents=True)
    foreign.write_bytes(b"ELF cross-platform payload")
    assert foreign not in validator._nested_candidates(
        app, app / "Contents/MacOS/ChatGPT"
    )


def test_macho_debug_symbol_is_not_a_nested_signing_target(tmp_path: Path) -> None:
    app = make_app(tmp_path)
    debug = app / "Contents/Resources/native/addon.node.dSYM/Contents/Resources/DWARF/addon.node"
    debug.parent.mkdir(parents=True)
    debug.write_bytes(b"\xcf\xfa\xed\xfe" + b"debug")
    assert debug not in validator._nested_candidates(
        app, app / "Contents/MacOS/ChatGPT"
    )


def test_malformed_entitlement_is_rejected(tmp_path: Path) -> None:
    app = make_app(tmp_path)
    runner = FakeRunner()
    runner.entitlements = "malformed"
    result = validate(app, runner)
    assert result["classification"] == "REJECT_ENTITLEMENTS"
    assert result["entitlements"]["status"] == "MALFORMED_XML_BLOB"


def test_asar_mismatch_is_rejected(tmp_path: Path) -> None:
    result = validate(make_app(tmp_path, integrity_matches=False), FakeRunner())
    assert result["classification"] == "REJECT_ASAR_INTEGRITY"
    assert result["asarIntegrity"]["status"] == "ASAR_INTEGRITY_MISMATCH"


def test_wrong_signing_identity_is_rejected(tmp_path: Path) -> None:
    runner = FakeRunner()
    runner.team_id = "WRONGTEAM"
    result = validate(make_app(tmp_path), runner)
    assert result["classification"] == "REJECT_IDENTITY"


def test_wrong_bundle_identifier_is_rejected(tmp_path: Path) -> None:
    result = validate(make_app(tmp_path, bundle_id="example.lookalike"), FakeRunner())
    assert result["classification"] == "REJECT_IDENTITY"


def test_current_app_is_never_accepted_as_clean_source(tmp_path: Path) -> None:
    app = make_app(tmp_path)
    result = validator.validate_candidate(app, runner=FakeRunner(), installed_app=app)
    assert result["classification"] == "REJECT_STRUCTURE"
    assert "untrusted reference" in result["reason"]


def test_multiple_candidates_are_all_validated(tmp_path: Path) -> None:
    downloads = tmp_path / "Downloads"
    downloads.mkdir()
    one = make_app(downloads, name="ChatGPT.app")
    two = make_app(downloads, name="ChatGPT-clean.app")
    seen: list[Path] = []

    def fake(candidate: Path):
        seen.append(candidate)
        return {
            "app": str(candidate),
            "classification": "CLEAN_REFERENCE_PASS" if candidate == two else "REJECT_SIGNATURE",
        }

    result = finder.discover_and_validate(
        home=tmp_path,
        volumes_root=tmp_path / "no-volumes",
        validator=fake,
        installed_app=tmp_path / "installed.app",
    )
    assert result["candidateCount"] == 2
    assert result["passCount"] == 1
    assert result["status"] == "CLEAN_REFERENCE_PASS"
    assert set(seen) == {one, two}


def test_no_candidate_requires_clean_official_app(tmp_path: Path) -> None:
    result = finder.discover_and_validate(
        home=tmp_path,
        volumes_root=tmp_path / "no-volumes",
        validator=lambda path: pytest.fail(f"unexpected candidate {path}"),
        installed_app=tmp_path / "installed.app",
    )
    assert result["candidateCount"] == 0
    assert result["status"] == "CLEAN_OFFICIAL_APP_REQUIRED"


def test_zero_mutation_guard_detects_runner_side_effect(tmp_path: Path) -> None:
    app = make_app(tmp_path)
    runner = FakeRunner()
    changed = False

    def mutate_once(_command) -> None:
        nonlocal changed
        if not changed:
            changed = True
            (app / "Contents/Resources/app.asar").write_bytes(b"mutated")

    runner.on_run = mutate_once
    with pytest.raises(validator.ReferenceValidationError) as caught:
        validate(app, runner)
    assert caught.value.code == "REFERENCE_MUTATED"
