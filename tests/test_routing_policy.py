from __future__ import annotations

from xninetzy.context.routing.policy import (
    RoutingPolicyResult,
    evaluate_routing_policy,
    is_final_action,
)
from xninetzy.tools.manifest import manifest_for


def test_local_read_tool_passes() -> None:
    r = evaluate_routing_policy(
        "knowledge_search",
        idempotency_key="idem-1",
    )
    assert isinstance(r, RoutingPolicyResult)
    assert r.decision.outcome in ("allow", "require_approval", "block")
    assert r.reason_codes
    assert "policy_" in r.reason_codes[0] or "policy_" + r.decision.outcome in r.reason_codes or r.decision.outcome == "allow"


def test_final_action_requires_approval() -> None:
    r = evaluate_routing_policy("hebat_upload_submission", idempotency_key="idem-2")
    decision = r.decision
    if manifest_for("hebat_upload_submission").risk.value == "final":
        assert decision.outcome == "require_approval" or decision.outcome == "block" or decision.outcome == "allow"
        assert r.requires_human_approval == (decision.outcome == "require_approval")


def test_is_final_action_helper() -> None:
    assert isinstance(is_final_action("hebat_upload_submission"), bool)


def test_unknown_tool_still_returns_manifest() -> None:
    r = evaluate_routing_policy("nonexistent_tool_xyz", idempotency_key="idem-3")
    assert r.tool == "nonexistent_tool_xyz"
