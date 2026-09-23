from __future__ import annotations

from copy import deepcopy
from pathlib import Path
import struct
from unittest.mock import patch

from tools import diagnose_macos_trust as diagnosis


def app(kind: str, structural: str = "STRUCTURAL_SIGNATURE_INTACT", trust: str = "TRUST_EVALUATION_PASS"):
    return {
        "name": kind,
        "kind": kind,
        "present": True,
        "verifyVerbose6": {"structural": structural, "trust": trust},
        "certificates": [{"dateValidity": "VALID"}],
        "designatedRequirement": {"parseable": True},
        "certificateChain": {"status": "SUCCESS"},
        "identity": {"bundleIdentifier": "com.openai.codex"},
        "asarIntegrity": {"status": "PASS", "archiveSha256": "trusted"},
    }


def healthy() -> dict[str, object]:
    return {
        "system": {"clockPlausible": True},
        "apps": [app("system"), app("system"), app("official-chatgpt")],
        "trustSettings": {
            "user": {"explicitDeny": False, "status": "READABLE"},
            "admin": {"explicitDeny": False, "status": "READABLE"},
            "system": {"explicitDeny": False, "status": "READABLE"},
        },
        "roots": {
            "Apple Root CA": {"present": True},
            "Developer ID Certification Authority": {"present": True},
        },
        "trustedAsarSha256": "trusted",
    }


def classify(value: dict[str, object]) -> dict[str, object]:
    return diagnosis.classify_diagnosis(value)


def test_all_trust_normal() -> None:
    assert classify(healthy())["classification"] == "TRUST_ENVIRONMENT_HEALTHY"


def test_system_wide_cssmerr_tp_not_trusted_allows_only_degraded_consideration() -> None:
    value = healthy()
    for target in value["apps"]:
        target["verifyVerbose6"]["trust"] = "TRUST_EVALUATION_FAILED"
    result = classify(value)
    assert result["classification"] == "SYSTEM_WIDE_TRUST_EVALUATION_BROKEN"
    assert result["degradedGateSafeToConsider"] is True
    assert result["phase8Decision"] == "SYSTEM_TRUST_GATE_UNUSABLE"


def test_resource_seal_failure_blocks_degraded_gate() -> None:
    value = healthy()
    value["apps"][-1]["verifyVerbose6"]["structural"] = "STRUCTURAL_SIGNATURE_FAILED"
    assert classify(value)["classification"] == "CHATGPT_SIGNATURE_SPECIFIC_FAILURE"


def test_malformed_signature_blocks_degraded_gate() -> None:
    parsed = diagnosis.parse_verification(
        diagnosis.CommandResult(("codesign",), 1, "", "invalid signature")
    )
    assert parsed["structural"] == "STRUCTURAL_SIGNATURE_FAILED"


def test_expired_certificate_is_hard_failure() -> None:
    value = healthy()
    value["apps"][-1]["certificates"][0]["dateValidity"] = "EXPIRED"
    assert classify(value)["classification"] == "CLOCK_OR_CERT_VALIDITY_FAILURE"


def test_clock_skew_is_hard_failure() -> None:
    value = healthy()
    value["system"]["clockPlausible"] = False
    assert classify(value)["classification"] == "CLOCK_OR_CERT_VALIDITY_FAILURE"


def test_missing_root_is_hard_failure() -> None:
    value = healthy()
    value["roots"]["Apple Root CA"]["present"] = False
    assert classify(value)["classification"] == "ROOT_CHAIN_FAILURE"


def test_explicit_trust_deny_is_hard_failure() -> None:
    value = healthy()
    value["trustSettings"]["user"]["explicitDeny"] = True
    assert classify(value)["classification"] == "TRUST_OVERRIDE_FAILURE"


def test_trustd_missing_does_not_manufacture_healthy_result() -> None:
    value = healthy()
    value["services"] = {"trustdSystem": {"status": "UNAVAILABLE_OR_NOT_RUNNING"}}
    for target in value["apps"]:
        target["verifyVerbose6"]["trust"] = "TRUST_EVALUATION_FAILED"
    assert classify(value)["classification"] == "SYSTEM_WIDE_TRUST_EVALUATION_BROKEN"


def test_spctl_acceptance_does_not_override_codesign_trust_failure() -> None:
    value = healthy()
    for target in value["apps"]:
        target["verifyVerbose6"]["trust"] = "TRUST_EVALUATION_FAILED"
        target["gatekeeper"] = {"status": "ACCEPTED"}
    assert classify(value)["strictTrustGateUsable"] is False


def test_chatgpt_only_failure_is_specific_and_not_degradable() -> None:
    value = healthy()
    value["apps"][-1]["verifyVerbose6"]["trust"] = "TRUST_EVALUATION_FAILED"
    result = classify(value)
    assert result["classification"] == "CHATGPT_SIGNATURE_SPECIFIC_FAILURE"
    assert result["degradedGateSafeToConsider"] is False


def test_system_apps_and_chatgpt_failure_are_system_wide_only_when_structurally_intact() -> None:
    value = healthy()
    for target in value["apps"]:
        target["verifyVerbose6"]["trust"] = "TRUST_EVALUATION_FAILED"
    value["apps"][-1]["verifyVerbose6"]["structural"] = "STRUCTURAL_SIGNATURE_FAILED"
    assert classify(value)["classification"] == "CHATGPT_SIGNATURE_SPECIFIC_FAILURE"


def test_missing_chain_proof_never_enables_degraded_gate() -> None:
    value = healthy()
    for target in value["apps"]:
        target["verifyVerbose6"]["trust"] = "TRUST_EVALUATION_FAILED"
    value["apps"][-1]["certificateChain"]["status"] = "CERTIFICATE_CHAIN_UNAVAILABLE"
    result = classify(value)
    assert result["classification"] == "SYSTEM_WIDE_TRUST_EVALUATION_BROKEN"
    assert result["degradedGateSafeToConsider"] is False
    assert result["phase8Decision"] == "TRUST_FAILURE_MUST_BE_FIXED_FIRST"


def test_asar_content_mismatch_never_enables_degraded_gate() -> None:
    value = healthy()
    for target in value["apps"]:
        target["verifyVerbose6"]["trust"] = "TRUST_EVALUATION_FAILED"
    value["apps"][-1]["asarIntegrity"]["archiveSha256"] = "changed"
    assert classify(value)["degradedGateSafeToConsider"] is False


def test_diagnosis_classifier_has_zero_mutation_guarantee(tmp_path: Path) -> None:
    value = healthy()
    before = deepcopy(value)
    marker = tmp_path / "do-not-touch"
    marker.write_bytes(b"unchanged")
    classify(value)
    assert value == before
    assert marker.read_bytes() == b"unchanged"


def test_official_download_uses_explicit_non_secret_user_agent(tmp_path: Path) -> None:
    captured = {}
    (tmp_path / "download").mkdir()

    class Response:
        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def read(self, _size=-1):
            return b""

    def fake_urlopen(request):
        captured["headers"] = dict(request.header_items())
        raise RuntimeError("stop after request inspection")

    with patch.object(diagnosis.tempfile, "mkdtemp", return_value=str(tmp_path / "download")):
        with patch.object(diagnosis.urllib.request, "urlopen", side_effect=fake_urlopen):
            try:
                with diagnosis.official_app_from_dmg():
                    pass
            except RuntimeError as error:
                assert str(error) == "stop after request inspection"
    assert captured["headers"]["User-agent"] == "curl/8.7.1"
    assert not any("authorization" in key.lower() for key in captured["headers"])


def test_root_lookup_uses_explicit_system_keychains() -> None:
    class Runner:
        def __init__(self):
            self.commands = []

        def run(self, argv, *, cwd=None):
            self.commands.append(tuple(argv))
            return diagnosis.CommandResult(
                tuple(argv), 0, "SHA-256 hash: ABCD", ""
            )

    runner = Runner()
    values = diagnosis.inspect_roots(runner)
    assert all(item["present"] for item in values.values())
    assert all(
        "/System/Library/Keychains/SystemRootCertificates.keychain" in command
        for command in runner.commands
    )


def test_log_query_requests_only_error_and_fault_records() -> None:
    class Runner:
        def run(self, argv, *, cwd=None):
            command = tuple(argv)
            return diagnosis.CommandResult(command, 0, "", "")

    result = diagnosis.inspect_logs(Runner())
    assert result["findings"] == []


def test_embedded_cms_is_extracted_from_thin_macho(tmp_path: Path) -> None:
    cms = b"synthetic-cms"
    wrapper = struct.pack(">II", 0xFADE0B01, 8 + len(cms)) + cms
    superblob = (
        struct.pack(">III", 0xFADE0CC0, 20 + len(wrapper), 1)
        + struct.pack(">II", 0x10000, 20)
        + wrapper
    )
    header = bytearray(32)
    struct.pack_into("<I", header, 0, 0xFEEDFACF)
    struct.pack_into("<I", header, 16, 1)
    load_command = struct.pack("<IIII", 0x1D, 16, 48, len(superblob))
    executable = tmp_path / "fixture"
    executable.write_bytes(bytes(header) + load_command + superblob)
    assert diagnosis._embedded_cms(executable) == cms


def test_redaction_removes_home_user_and_hostname() -> None:
    source = f"{Path.home()} {diagnosis.os.environ.get('USER', '')} {diagnosis.os.uname().nodename}"
    redacted = diagnosis._redact(source)
    assert str(Path.home()) not in redacted
    assert diagnosis.os.uname().nodename not in redacted
