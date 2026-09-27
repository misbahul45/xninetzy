from __future__ import annotations

import logging

from xninetzy.os.security.pii_filter import (
    PIIRedactionFilter,
    install_pii_filter,
    pii_summary,
    redact_pii,
)


def test_redact_pii_masks_email_addresses():
    redacted, hits = redact_pii("contact user@example.com for details")
    assert "user@example.com" not in redacted
    assert "[REDACTED:email]" in redacted
    assert hits["email"] == 1


def test_redact_pii_masks_indonesian_phone_numbers():
    redacted, hits = redact_pii("call +62 812 3456 7890 today")
    assert "+62 812 3456 7890" not in redacted
    assert hits["phone_id"] == 1


def test_redact_pii_masks_generic_e164_phones():
    redacted, hits = redact_pii("ring +1 415 555 1234 anytime")
    assert "[REDACTED:phone_e164]" in redacted
    assert hits["phone_e164"] == 1


def test_redact_pii_masks_credit_card_numbers():
    redacted, hits = redact_pii("card 4111 1111 1111 1111 on file")
    assert "[REDACTED:card]" in redacted
    assert hits["card"] == 1


def test_redact_pii_masks_nik_indonesian_id():
    redacted, hits = redact_pii("NIK 3201234567890001 here")
    assert "[REDACTED:nik]" in redacted
    assert hits["nik"] == 1


def test_redact_pii_masks_bearer_tokens():
    redacted, hits = redact_pii("Authorization: Bearer abc123def456ghi789jkl012mno")
    assert "[REDACTED:token_bearer]" in redacted
    assert hits["token_bearer"] == 1


def test_redact_pii_masks_basic_tokens():
    redacted, hits = redact_pii("Authorization: Basic dXNlcjpwYXNzMTIzNDU2Nzg5MA==")
    assert "[REDACTED:token_basic]" in redacted
    assert hits["token_basic"] == 1


def test_redact_pii_masks_api_keys():
    redacted, hits = redact_pii('api_key="sk-abcdef1234567890abcdef"')
    assert "[REDACTED:token_api_key]" in redacted
    assert hits["token_api_key"] == 1


def test_redact_pii_masks_session_cookies():
    redacted, hits = redact_pii("Cookie: sid=abcdef1234567890abcdef")
    assert "[REDACTED:cookie_session]" in redacted
    assert hits["cookie_session"] == 1


def test_redact_pii_handles_empty_input():
    redacted, hits = redact_pii("")
    assert redacted == ""
    assert hits == {}


def test_redact_pii_handles_clean_input():
    text = "no secrets here just a normal log line about a job posting"
    redacted, hits = redact_pii(text)
    assert redacted == text
    assert hits == {}


def test_redact_pii_aggregates_multiple_categories():
    text = "user alice@example.com with NIK 3201234567890001 called +62 812 3456 7890"
    redacted, hits = redact_pii(text)
    assert hits["email"] == 1
    assert hits["nik"] == 1
    assert hits["phone_id"] == 1
    assert "alice@example.com" not in redacted
    assert "3201234567890001" not in redacted


def test_redact_pii_preserves_surrounding_text():
    text = "before alice@example.com after"
    redacted, _ = redact_pii(text)
    assert redacted.startswith("before ")
    assert redacted.endswith(" after")


def test_pii_redaction_filter_applies_to_log_records():
    flt = PIIRedactionFilter()
    record = logging.LogRecord(
        name="test",
        level=logging.INFO,
        pathname="x.py",
        lineno=1,
        msg="contact user@example.com about job",
        args=(),
        exc_info=None,
    )
    flt.filter(record)
    assert "user@example.com" not in record.msg
    assert "[REDACTED:email]" in record.msg
    assert flt.summary()["email"] == 1


def test_pii_redaction_filter_idempotent():
    flt = PIIRedactionFilter()
    for _ in range(3):
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="x.py",
            lineno=1,
            msg="user@example.com",
            args=(),
            exc_info=None,
        )
        flt.filter(record)
    assert flt.summary()["email"] == 3


def test_install_pii_filter_attaches_to_logger():
    logger = logging.getLogger("xninetzy.test.pii_install")
    logger.handlers = []
    logger.setLevel(logging.INFO)
    handler = logging.StreamHandler()
    logger.addHandler(handler)
    flt = install_pii_filter(logger)
    logger.info("contact user@example.com")
    assert flt.summary()["email"] >= 1


def test_pii_summary_returns_counts_copy():
    flt = PIIRedactionFilter()
    record = logging.LogRecord(
        name="t",
        level=logging.INFO,
        pathname="x",
        lineno=1,
        msg="a@b.co",
        args=(),
        exc_info=None,
    )
    flt.filter(record)
    snap = pii_summary(flt)
    snap["email"] = 999
    assert flt.summary()["email"] == 1