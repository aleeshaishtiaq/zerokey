import json

from src.data_pipeline.device_mapping import (
    _feature_table,
    _live_null_summary,
    _rows_with_null_features,
    _validate_feature_records,
    live_device_mapping,
    ub_device_mapping,
    verify_feature_tables,
)
from src.data_pipeline.features import BehavioralFeatureSummary


def _ub_record(user_id="001", device_id="a" * 64):
    return BehavioralFeatureSummary(
        subject_id=user_id,
        user_id=user_id,
        device_id=device_id,
        session=0,
        keyboard_code=0,
        task_id=0,
        subset="baseline",
        original_filename="001000.txt",
        keyboard_features={"pause_count": 0},
        mouse_features={"path_length_px": 0, "displacement_px": 0},
    ).model_dump(mode="python")


def _live_record():
    return {
        "collection_version": 2,
        "user_id": "provider|live-user",
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


def test_mapping_files_keep_live_pairs_and_stably_hash_each_ub_user():
    live = _live_record()
    assert live_device_mapping([live, live]) == [
        {"user_id": live["user_id"], "device_id": live["device_id"]}
    ]

    ub_records = [_ub_record("001"), _ub_record("002")]
    first = ub_device_mapping(ub_records)
    second = ub_device_mapping(list(reversed(ub_records)))

    assert first == second
    assert len(first) == 2
    assert all(len(item["device_id"]) == 64 for item in first)
    assert first[0]["device_id"] != first[1]["device_id"]


def test_feature_tables_exclude_device_and_report_nulls_with_matching_schema():
    live_input = _live_record()
    ub_records = _validate_feature_records([_ub_record()], source="test UB")
    live_records = _validate_feature_records(
        [
            {
                **_ub_record(),
                "mouse_features": {
                    "path_length_px": 0,
                    "displacement_px": 0,
                    "average_velocity_px_per_second": 0,
                    "direction_changes_per_second": 0,
                    "straightness_ratio": None,
                    "click_interval_ticks_mean": None,
                },
            }
        ],
        source="test live",
    )
    df_ub = _feature_table(ub_records)
    df_live = _feature_table(live_records)
    schema = verify_feature_tables(df_ub, df_live)
    nulls = _live_null_summary(df_live, [live_input])

    assert schema["schema_matches"] is True
    assert schema["device_id_excluded"] is True
    assert schema["column_order_matches"] is True
    click_interval = "mouse_features.click_interval_ticks_mean"
    assert df_live["rows"][0][click_interval] is None
    assert _rows_with_null_features(df_live) == 1
    assert next(
        item for item in nulls
        if item["feature"] == "mouse_features.click_interval_ticks_mean"
    ) == {
        "feature": "mouse_features.click_interval_ticks_mean",
        "null_count": 1,
        "missing_in_source_count": 0,
    }
    assert json.dumps(df_live["rows"], allow_nan=False)


def test_feature_schema_verifier_reports_order_and_dtype_mismatches():
    records = _validate_feature_records([_ub_record()], source="UB")
    expected = _feature_table(records)
    reordered = {
        "columns": list(reversed(expected["columns"])),
        "rows": expected["rows"],
    }
    reordered["columns"][0] = {**reordered["columns"][0], "dtype": "int64"}

    report = verify_feature_tables(expected, reordered)

    assert report["schema_matches"] is False
    assert report["column_order_matches"] is False
    assert report["dtypes_match"] is False
