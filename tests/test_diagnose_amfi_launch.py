from __future__ import annotations

import importlib.util
from pathlib import Path


MODULE_PATH = Path(__file__).resolve().parents[1] / "tools/diagnose_amfi_launch.py"
spec = importlib.util.spec_from_file_location("diagnose_amfi_launch", MODULE_PATH)
module = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(module)


def test_generic_amfi_rejection_does_not_invent_a_named_entitlement() -> None:
    sample = (
        'Restricted entitlements not validated, bailing out. '
        'Unable to retrieve certificate chain\n'
        'Adhoc signed app with restricted entitlements detected\n'
        '/private/tmp/test/ChatGPT.app/Contents/MacOS/ChatGPT not valid: '
        'AppleMobileFileIntegrityError Code=-424 '
        '"The file is adhoc signed but contains restricted entitlements"'
    )
    evidence = module.parse_amfi_log(sample)
    assert evidence["failedExecutable"] == "Contents/MacOS/ChatGPT"
    assert evidence["failureClass"] == "ENTITLEMENT_AUTHORIZATION_FAILED"
    assert evidence["amfiCode427"] is True
    assert evidence["namedUnsatisfiedEntitlements"] == []
    assert evidence["verdict"] == "AMFI_CAUSE_UNCONFIRMED"


def test_explicit_unsatisfied_entitlement_can_open_experiment_gate() -> None:
    sample = (
        'Adhoc signed app with restricted entitlements detected\n'
        '/tmp/test/ChatGPT.app/Contents/MacOS/ChatGPT not valid: '
        'AppleMobileFileIntegrityError Code=-424\n'
        'Unsatisfied Entitlements: keychain-access-groups'
    )
    evidence = module.parse_amfi_log(sample)
    assert evidence["namedUnsatisfiedEntitlements"] == ["keychain-access-groups"]
    assert evidence["verdict"] == "EXACT_ENTITLEMENT_IDENTIFIED"


def test_all_official_keys_are_classified_without_guessing_unknown_keys() -> None:
    classified = module.classify_entitlements(list(module.CLASSES))
    assert len(classified) == 14
    assert classified["keychain-access-groups"] == "RESTRICTED"
    assert classified["com.apple.developer.aps-environment"] == "RESTRICTED"
    assert classified["com.apple.application-identifier"] == "UNKNOWN"
    assert classified["com.apple.security.cs.allow-jit"] == "UNRESTRICTED"
    assert module.classify_entitlements(["private.unknown"])["private.unknown"] == "UNKNOWN"


def test_missing_rejection_is_not_misclassified_as_entitlement_failure() -> None:
    evidence = module.parse_amfi_log("unrelated renderer exit")
    assert evidence["failedExecutable"] is None
    assert evidence["failureClass"] == "UNKNOWN"
    assert evidence["verdict"] == "AMFI_CAUSE_UNCONFIRMED"


def test_signing_experiment_gate_requires_a_named_signed_restricted_claim() -> None:
    signed = {"keychain-access-groups", "com.apple.security.cs.allow-jit"}
    baseline = {"failedExecutable": "Contents/MacOS/ChatGPT", "namedUnsatisfiedEntitlements": []}
    assert module.experiment_evidence_gate(baseline, signed)["reducedSigningPlanMayBeReviewed"] is False
    named = {**baseline, "namedUnsatisfiedEntitlements": ["keychain-access-groups"]}
    allowed = module.experiment_evidence_gate(named, signed)
    assert allowed["reducedSigningPlanMayBeReviewed"] is True
    assert allowed["launchAuthorizedByThisGate"] is False
    for key in ("com.apple.security.cs.allow-jit", "com.apple.private.unlisted"):
        assert module.experiment_evidence_gate(
            {**baseline, "namedUnsatisfiedEntitlements": [key]}, signed
        )["reducedSigningPlanMayBeReviewed"] is False
