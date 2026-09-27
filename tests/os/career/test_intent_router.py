from __future__ import annotations


def test_parse_intent_extracts_role_terms():
    from xninetzy.domains.career.intent import parse_intent

    intent = parse_intent("Senior Backend Engineer Intern, Jakarta")
    assert "backend" in intent.role_terms
    assert "engineer" in intent.role_terms
    assert "senior" not in intent.role_terms
    assert "intern" not in intent.role_terms


def test_parse_intent_detects_remote():
    from xninetzy.domains.career.intent import parse_intent

    intent = parse_intent("remote backend engineer")
    assert intent.work_mode == "remote"


def test_parse_intent_detects_indonesia_country_hint():
    from xninetzy.domains.career.intent import parse_intent

    intent = parse_intent("backend engineer jakarta")
    assert intent.country_code == "ID"


def test_parse_intent_detects_seniority():
    from xninetzy.domains.career.intent import parse_intent

    intent = parse_intent("mid-level frontend developer")
    assert intent.seniority == "mid"


def test_parse_intent_detects_employment():
    from xninetzy.domains.career.intent import parse_intent

    intent = parse_intent("internship data scientist")
    assert intent.employment_type == "internship"


def test_parse_intent_respects_country_override():
    from xninetzy.domains.career.intent import parse_intent

    intent = parse_intent("engineer jakarta", country="US")
    assert intent.country_code == "US"


def test_parse_intent_respects_work_mode_override():
    from xninetzy.domains.career.intent import parse_intent

    intent = parse_intent("backend engineer", work_mode="onsite")
    assert intent.work_mode == "onsite"


def test_parse_intent_handles_empty_input():
    from xninetzy.domains.career.intent import parse_intent

    intent = parse_intent("")
    assert intent.role_terms == ()
    assert intent.work_mode == "any"
    assert intent.country_code == ""


def test_parse_intent_handles_unicode_tokens():
    from xninetzy.domains.career.intent import parse_intent

    intent = parse_intent("lowongan programmer surabaya")
    assert "programmer" in intent.role_terms
    assert intent.country_code == "ID"


def test_parse_intent_handles_plus_in_query():
    from xninetzy.domains.career.intent import parse_intent

    intent = parse_intent("c++ developer remote")
    assert "c++" in intent.role_terms
    assert intent.work_mode == "remote"


def test_parse_intent_handles_dot_in_query():
    from xninetzy.domains.career.intent import parse_intent

    intent = parse_intent("node.js backend developer")
    assert "node.js" in intent.role_terms


def test_parse_intent_flags_needs_sampling_for_ambiguous():
    from xninetzy.domains.career.intent import parse_intent

    intent = parse_intent("jobs")
    assert intent.needs_sampling is True


def test_parse_intent_does_not_flag_deterministic_for_concrete_role():
    from xninetzy.domains.career.intent import parse_intent

    intent = parse_intent("senior backend engineer remote")
    assert intent.needs_sampling is False
