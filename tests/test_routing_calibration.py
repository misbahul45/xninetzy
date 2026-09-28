from __future__ import annotations

from xninetzy.context.routing.calibration import (
    CalibrationRecord,
    CalibrationRegistry,
    CALIBRATION_MIN_SAMPLES,
    apply_calibration,
    brier,
    ece,
    fit_platt,
    health_snapshot,
)


def test_ece_handles_small_inputs() -> None:
    assert ece([], []) == 0.0
    assert 0.0 <= ece([0.5], [1]) <= 1.0


def test_brier_returns_zero_for_perfect() -> None:
    assert brier([0.0, 1.0, 0.0], [0, 1, 0]) == 0.0


def test_fit_platt_handles_minimum_input() -> None:
    a, b = fit_platt([0.1, 0.9], [0, 1])
    assert isinstance(a, float) and isinstance(b, float)


def test_calibration_registry_round_trip(tmp_path) -> None:
    reg = CalibrationRegistry(storage_dir=tmp_path)
    rec = CalibrationRecord(
        layer="L2_domain",
        domain="research",
        coefficients=(2.5, -0.5),
        n_samples=200,
        ece=0.04,
        brier=0.08,
        trained_at="2026-09-28T00:00:00+00:00",
        train_split_hash="abc123",
    )
    reg.register(rec)
    out = reg.lookup("L2_domain", "research")
    assert out is not None
    assert out.ece == 0.04
    assert reg.is_acceptable(out)


def test_apply_calibration_clamps_extremes() -> None:
    out = apply_calibration({"a": 0.0, "b": 1.0}, (10.0, 0.0))
    assert 0.0 <= out["a"] <= 1.0
    assert 0.0 <= out["b"] <= 1.0


def test_health_snapshot_includes_global_count(tmp_path) -> None:
    reg = CalibrationRegistry(storage_dir=tmp_path)
    h = health_snapshot(reg)
    assert "registries" in h
    assert h["min_samples_required"] == CALIBRATION_MIN_SAMPLES
