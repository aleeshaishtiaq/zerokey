import pytest

from src.api.routes import TelemetryPayload
from src.data_pipeline.features import (
    BehavioralFeatureSummary,
    KeyboardFeatureSummary,
    MouseFeatureSummary,
)
from src.data_pipeline.sanity_check import compare_records, verify_schema


def _ub_record(path_length, dwell_ms, pause_count):
    return {
        "mouse_features": {
            "path_length_px": path_length,
            "displacement_px": path_length,
            "straightness_ratio": 1,
            "click_interval_ticks_mean": 20,
        },
        "keyboard_features": {
            "dwell_time_ms_mean": dwell_ms,
            "pause_count": pause_count,
            "rollover_ratio": 0.1,
        },
    }


def _live_record(path_length, dwell_ms, pause_count):
    return {
        "mouse_features": {
            "path_length_px": path_length,
            "displacement_px": path_length,
            "straightness_ratio": 1,
        },
        "keyboard_features": {
            "dwell_time_ms_mean": dwell_ms,
            "pause_count": pause_count,
            "rollover_ratio": 0.1,
        },
    }


def test_sanity_check_compares_features_with_aligned_units():
    report = compare_records(
        [_ub_record(value, value * 10, 1) for value in range(1, 21)],
        [_live_record(value, value * 10, 1) for value in range(1, 21)],
    )

    checks = {item["feature"]: item for item in report["distribution_checks"]}
    assert checks["keyboard.dwell_time_ms_mean"]["ub_mean"] == pytest.approx(105)
    assert checks["keyboard.dwell_time_ms_mean"]["status"] == "not_rejected"
    assert checks["mouse.path_length_px"]["status"] == "not_rejected"


def test_sanity_check_reports_distribution_shift():
    report = compare_records(
        [_ub_record(path, 100, 1) for path in range(1, 21)],
        [_live_record(path, 100, 1) for path in range(100, 120)],
    )

    assert report["status"] == "review_distribution_differences"


def test_sanity_check_does_not_pass_when_sample_cannot_reject_any_distribution():
    report = compare_records(
        [_ub_record(path, 100, 1) for path in (10, 20, 30)],
        [_live_record(path, 100, 1) for path in (100, 200, 300)],
    )

    assert report["status"] == "inconclusive_insufficient_samples"


def test_sanity_check_flags_missing_ub_timebase():
    ub_record = _ub_record(10, 100, 1)
    report = compare_records([ub_record], [_live_record(10, 100, 1)])

    assert "mouse.click_interval_ms_mean" in report["schema"]["ub_timing_unit_missing"]


def test_schema_verification_reports_live_and_ub_contract_differences():
    ub_record = BehavioralFeatureSummary(
        subject_id="001",
        user_id="001",
        device_id="a" * 64,
        session=0,
        keyboard_code=0,
        task_id=0,
        subset="baseline",
        original_filename="001000.txt",
        keyboard_features=KeyboardFeatureSummary(pause_count=0),
        mouse_features=MouseFeatureSummary(path_length_px=0, displacement_px=0),
    ).model_dump(mode="json")
    live_record = TelemetryPayload.model_validate(
        {
            "collection_version": 2,
            "user_id": "approved",
            "device_id": "b" * 64,
            "session_id": "46c1e8f2-4c26-4b91-88d9-0c344aa3d552",
            "timestamp": "2026-11-18T08:27:00+00:00",
            "public_ip_address": None,
            "mouse_features": {
                "path_length_px": 0,
                "displacement_px": 0,
                "average_velocity_px_per_second": 0,
                "direction_changes_per_second": 0,
                "straightness_ratio": None,
                "click_interval_ms_mean": None,
            },
            "keyboard_features": {
                "dwell_time_ms_mean": None,
                "dwell_time_ms_stddev": None,
                "pp_latency_ms_mean": None,
                "pp_latency_ms_stddev": None,
                "rp_latency_ms_mean": None,
                "rp_latency_ms_stddev": None,
                "typing_rate_keystrokes_per_minute": 0,
                "pause_count": 0,
                "pause_duration_ms_mean": None,
                "inter_key_interval_ms_stddev": None,
                "rollover_ratio": 0,
            },
        }
    ).model_dump(mode="json")

    report = verify_schema([ub_record], [live_record])

    assert report["records_validate_against_own_models"] == {"ub": True, "live": True}
    assert report["exact_feature_keys_match"] is False
    assert report["feature_key_differences"]["mouse"] == {
        "ub_only": ["click_interval_ticks_mean"],
        "live_only": ["click_interval_ms_mean"],
    }
    assert "click_interval_ticks_mean" in report["mouse_click_interval"]["ub_field"]
    assert report["mouse_click_interval"]["ub_timebase"] == [("unverified", None)]
    assert report["mouse_click_interval"]["comparable"] is False
    assert {
        item["field"]
        for item in report["field_contract_differences"]
    } >= {
        "mouse_features.average_velocity_px_per_second",
        "mouse_features.direction_changes_per_second",
        "keyboard_features.typing_rate_keystrokes_per_minute",
        "keyboard_features.rollover_ratio",
    }


def test_schema_verification_reports_invalid_records_without_aborting_comparison():
    report = compare_records(
        [{"mouse_features": [], "keyboard_features": {}}],
        [],
    )

    assert report["schema_verification"]["records_validate_against_own_models"] == {
        "ub": False,
        "live": True,
    }
    assert report["schema_verification"]["validation_errors"]["ub"]["count"] == 1
