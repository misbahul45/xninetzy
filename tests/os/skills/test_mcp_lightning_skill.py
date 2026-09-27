import pytest

from xninetzy.skills.registry import get_skill, rank_skills


def test_mcp_lightning_skill_is_discoverable_and_valid():
    skill = get_skill("xninetzy-mcp-lightning")

    assert skill is not None, "xninetzy-mcp-lightning harus loadable"
    assert skill.description, "description harus ter-ekstrak dari YAML frontmatter"
    assert skill.line_count > 0, "body harus ter-load"
    assert skill.resource_paths, "skill harus punya resource paths (progressive disclosure)"


def test_mcp_lightning_skill_routes_optimization_requests():
    skill = get_skill("xninetzy-mcp-lightning")
    if skill is None:
        pytest.skip("xninetzy-mcp-lightning belum loadable")

    matches = rank_skills(
        "optimasi MCP RL contextual bandit provider dan deep research evidence",
        limit=5,
    )
    skill_names = [m.skill.name for m in matches]
    assert "xninetzy-mcp-lightning" in skill_names, (
        f"expected xninetzy-mcp-lightning in top-5 ranking, got {skill_names}"
    )

