from __future__ import annotations


def test_text_input_is_safe():
    from xninetzy.os.career.safe_fields import classify_field

    field = classify_field(name="full_name", field_type="text", selector="#full_name")
    assert field.safe_to_fill is True


def test_email_input_is_safe():
    from xninetzy.os.career.safe_fields import classify_field

    field = classify_field(name="email", field_type="email")
    assert field.safe_to_fill is True


def test_textarea_is_safe():
    from xninetzy.os.career.safe_fields import classify_field

    field = classify_field(name="cover_letter", field_type="textarea")
    assert field.safe_to_fill is True


def test_password_input_is_unsafe():
    from xninetzy.os.career.safe_fields import classify_field

    field = classify_field(name="password", field_type="password")
    assert field.safe_to_fill is False
    assert "unsafe input type" in field.safety_reason


def test_submit_button_is_unsafe():
    from xninetzy.os.career.safe_fields import classify_field

    field = classify_field(name="submit", field_type="submit")
    assert field.safe_to_fill is False
    assert "submit" in field.safety_reason.lower()


def test_file_input_is_unsafe():
    from xninetzy.os.career.safe_fields import classify_field

    field = classify_field(name="resume_upload", field_type="file")
    assert field.safe_to_fill is False


def test_hidden_input_is_unsafe():
    from xninetzy.os.career.safe_fields import classify_field

    field = classify_field(name="csrf_token", field_type="hidden")
    assert field.safe_to_fill is False


def test_field_with_unsafe_name_is_blocked():
    from xninetzy.os.career.safe_fields import classify_field

    field = classify_field(name="credit_card", field_type="text")
    assert field.safe_to_fill is False
    assert "unsafe pattern" in field.safety_reason


def test_field_with_consent_name_is_blocked():
    from xninetzy.os.career.safe_fields import classify_field

    field = classify_field(name="agree_to_tos", field_type="checkbox")
    assert field.safe_to_fill is False


def test_unknown_field_is_blocked_by_default():
    from xninetzy.os.career.safe_fields import classify_field

    field = classify_field(name="weird_thing", field_type="password")
    assert field.safe_to_fill is False


def test_partition_by_safety_separates_safe_and_unsafe():
    from xninetzy.os.career.safe_fields import classify_field, partition_by_safety

    fields = [
        classify_field(name="full_name", field_type="text"),
        classify_field(name="password", field_type="password"),
        classify_field(name="cover_letter", field_type="textarea"),
        classify_field(name="submit", field_type="submit"),
    ]
    safe, unsafe = partition_by_safety(fields)
    assert len(safe) == 2
    assert len(unsafe) == 2
    assert {f.name for f in safe} == {"full_name", "cover_letter"}
    assert {f.name for f in unsafe} == {"password", "submit"}


def test_classifier_returns_full_metadata():
    from xninetzy.os.career.safe_fields import classify_field

    field = classify_field(
        name="email",
        field_type="email",
        label="Email Address",
        required=True,
        selector="input[name=email]",
        current_value="user@example.com",
    )
    assert field.label == "Email Address"
    assert field.required is True
    assert field.selector == "input[name=email]"
    assert field.current_value == "user@example.com"
