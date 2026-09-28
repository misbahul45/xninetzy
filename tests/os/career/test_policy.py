"""Test source policy gate semantics."""

from __future__ import annotations

from xninetzy.os.career.acquisition.policy import (
    AutomationScope,
    PolicyStatus,
    SourcePolicy,
    SourcePolicyGate,
)


def test_unknown_source_returns_unknown_status() -> None:
    gate = SourcePolicyGate()
    verdict = gate.evaluate("not_registered")
    assert verdict.status == PolicyStatus.UNKNOWN
    assert verdict.can_fetch is False
    assert verdict.recommended_action == "OPEN_POLICY_REVIEW_TICKET"


def test_blocked_source_cannot_fetch_on_any_transport() -> None:
    gate = SourcePolicyGate()
    gate.register(
        SourcePolicy(
            source_id="blocked",
            status=PolicyStatus.BLOCKED,
            allowed_transports=("API", "HTTP", "BROWSER"),
            blocked_reason="tos_violation",
        )
    )
    for transport in (None, "API", "HTTP", "BROWSER"):
        verdict = gate.evaluate("blocked", transport=transport)
        assert verdict.can_fetch is False
        assert verdict.recommended_action == "STOP_DO_NOT_SCRAPE"


def test_api_only_source_rejects_browser_transport() -> None:
    gate = SourcePolicyGate()
    gate.register(
        SourcePolicy(
            source_id="kalibrr",
            status=PolicyStatus.API_ONLY,
            allowed_transports=("API",),
        )
    )
    verdict = gate.evaluate("kalibrr", transport="BROWSER")
    assert verdict.can_fetch is False
    assert verdict.recommended_action == "USE_DOCUMENTED_API"
    api_verdict = gate.evaluate("kalibrr", transport="API")
    assert api_verdict.can_fetch is True


def test_user_authorized_only_source_blocks_without_login() -> None:
    gate = SourcePolicyGate()
    gate.register(
        SourcePolicy(
            source_id="linkedin",
            status=PolicyStatus.USER_AUTHORIZED_ONLY,
            allowed_transports=("BROWSER",),
            automation_scope=AutomationScope.READ,
        )
    )
    verdict = gate.evaluate("linkedin", requires_user_login=False)
    assert verdict.can_fetch is False
    assert verdict.requires_user_login is True
    assert verdict.recommended_action == "REQUEST_USER_LOGIN"


def test_allowed_source_default_permits_api_when_in_transports() -> None:
    gate = SourcePolicyGate()
    gate.register(
        SourcePolicy(
            source_id="remoteok",
            status=PolicyStatus.ALLOWED,
            allowed_transports=("API",),
        )
    )
    verdict = gate.evaluate("remoteok", transport="API")
    assert verdict.can_fetch is True
    assert verdict.can_use_documented_api is True
    assert verdict.recommended_action == "PROCEED"


def test_load_default_policies_seeds_known_sources() -> None:
    from xninetzy.os.career.acquisition.policy import (
        build_default_gate,
        load_default_policies,
    )

    policies = load_default_policies()
    sources = {p.source_id for p in policies}
    assert {"remoteok", "arbeitnow", "kalibrr", "glints", "dealls", "jobstreet_id"} <= sources
    gate = build_default_gate()
    assert gate.list_known()  # non-empty
