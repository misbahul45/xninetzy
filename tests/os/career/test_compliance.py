from __future__ import annotations


def test_declare_and_get_roundtrip():
    from xninetzy.os.career.compliance import ComplianceClass, declare, get

    declare(
        "test_adapter",
        tos_url="https://example.com/tos",
        declared_class=ComplianceClass.READ,
        notes="manual",
    )
    fetched = get("test_adapter")
    assert fetched is not None
    assert fetched.adapter_id == "test_adapter"
    assert fetched.declared_class is ComplianceClass.READ
    assert fetched.tos_url == "https://example.com/tos"


def test_audit_returns_known_adapters():
    from xninetzy.os.career.compliance import audit

    report = audit()
    assert report["total_adapters"] >= 6
    assert any(r["adapter"] == "remoteok" for r in report["rows"])


def test_audit_marks_unacknowledged_risks_as_drift():
    from xninetzy.os.career.compliance import ComplianceClass, audit, declare

    declare(
        "fixture_drift",
        tos_url="https://x/tos",
        declared_class=ComplianceClass.READ,
        risk_acknowledged=False,
    )
    report = audit()
    assert report["status"] == "drift"
    assert "fixture_drift" in report["drift"]


def test_can_permit_read_for_read_class():
    from xninetzy.os.career.compliance import ComplianceClass, can_perform

    allowed, reason = can_perform("remoteok", ComplianceClass.READ)
    assert allowed is True
    assert reason == "ok"


def test_can_refuse_submit_for_read_class():
    from xninetzy.os.career.compliance import ComplianceClass, can_perform

    allowed, reason = can_perform("remoteok", ComplianceClass.SUBMIT)
    assert allowed is False
    assert "not permitted" in reason


def test_can_refuse_read_for_never_class():
    from xninetzy.os.career.compliance import ComplianceClass, can_perform

    allowed, reason = can_perform("jobstreet_id", ComplianceClass.READ)
    assert allowed is False
    assert "NEVER" in reason


def test_can_refuse_unknown_adapter():
    from xninetzy.os.career.compliance import ComplianceClass, can_perform

    allowed, reason = can_perform("not_registered", ComplianceClass.READ)
    assert allowed is False
    assert "no compliance declaration" in reason
