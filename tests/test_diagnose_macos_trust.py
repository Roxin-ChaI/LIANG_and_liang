from __future__ import annotations

from copy import deepcopy
from pathlib import Path

from tools import diagnose_macos_trust as diagnosis


def app(kind: str, structural: str = "STRUCTURAL_SIGNATURE_INTACT", trust: str = "TRUST_EVALUATION_PASS"):
    return {
        "name": kind,
        "kind": kind,
        "present": True,
        "verifyVerbose6": {"structural": structural, "trust": trust},
        "certificates": [{"dateValidity": "VALID"}],
    }


def healthy() -> dict[str, object]:
    return {
        "system": {"clockPlausible": True},
        "apps": [app("system"), app("system"), app("official-chatgpt")],
        "trustSettings": {
            "user": {"explicitDeny": False},
            "admin": {"explicitDeny": False},
            "system": {"explicitDeny": False},
        },
        "roots": {
            "Apple Root CA": {"present": True},
            "Developer ID Certification Authority": {"present": True},
        },
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


def test_diagnosis_classifier_has_zero_mutation_guarantee(tmp_path: Path) -> None:
    value = healthy()
    before = deepcopy(value)
    marker = tmp_path / "do-not-touch"
    marker.write_bytes(b"unchanged")
    classify(value)
    assert value == before
    assert marker.read_bytes() == b"unchanged"
