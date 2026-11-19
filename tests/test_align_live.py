import json
from pathlib import Path

import pytest

from src.data_pipeline.align_live import align_records, _write_jsonl
from src.data_pipeline.features import BehavioralFeatureSummary


def _live_record(click_interval_ms, *, user_id="provider|live-user", session_id=None):
    return {
        "collection_version": 2,
        "user_id": user_id,
        "device_id": "a" * 64,
        "session_id": session_id or "46c1e8f2-4c26-4b91-88d9-0c344aa3d552",
        "timestamp": "2026-11-18T08:27:00+00:00",
        "public_ip_address": None,
        "mouse_features": {
            "path_length_px": 100,
            "displacement_px": 80,
            "average_velocity_px_per_second": 200,
            "direction_changes_per_second": 1,
            "straightness_ratio": 0.8,
            "click_interval_ms_mean": click_interval_ms,
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


def test_align_records_matches_ub_model_and_converts_click_intervals():
    converted = align_records(
        [_live_record(1629.5), _live_record(None)],
        reserved_ub_subject_ids={1, 2, 3},
    )

    assert len(converted) == 2
    first = BehavioralFeatureSummary.model_validate(converted[0])
    second = BehavioralFeatureSummary.model_validate(converted[1])
    assert set(converted[0]) == set(BehavioralFeatureSummary.model_fields)
    assert set(first.mouse_features.model_dump()) == set(
        BehavioralFeatureSummary.model_fields["mouse_features"].annotation.model_fields
    )
    assert first.mouse_features.click_interval_ticks_mean == 1629.5
    assert second.mouse_features.click_interval_ticks_mean is None
    assert first.mouse_ticks_per_second == 1000
    assert first.mouse_timestamp_unit == "milliseconds"
    assert first.user_id == first.subject_id
    assert first.original_filename == (
        f"{first.subject_id}{first.session}{first.keyboard_code}{first.task_id}.txt"
    )
    assert first.keyboard_features.dwell_time_ms_mean is None


def test_align_records_retains_rows_with_null_optional_features():
    converted = align_records(
        [_live_record(None)],
        reserved_ub_subject_ids=set(),
    )

    assert len(converted) == 1
    assert converted[0]["keyboard_features"]["dwell_time_ms_mean"] is None
    assert converted[0]["mouse_features"]["click_interval_ticks_mean"] is None
    assert converted[0]["mouse_features"]["straightness_ratio"] == 0.8


def test_subject_codes_avoid_processed_ub_subjects_and_are_repeatable():
    live = [_live_record(1.0)]

    first = align_records(live, reserved_ub_subject_ids={1, 2, 3})
    second = align_records(live, reserved_ub_subject_ids={1, 2, 3})

    assert first == second
    assert int(first[0]["subject_id"]) not in {1, 2, 3}


def test_aligner_rejects_more_sessions_than_ub_schema_can_represent():
    records = [
        _live_record(
            1.0,
            session_id=f"00000000-0000-0000-0000-{value:012d}",
        )
        for value in range(4)
    ]

    with pytest.raises(ValueError, match="session"):
        align_records(records, reserved_ub_subject_ids=set())


def test_writer_does_not_replace_an_existing_file_without_opt_in(tmp_path: Path):
    output = tmp_path / "aligned.jsonl"
    output.write_text('{"keep": true}\n', encoding="utf-8")

    with pytest.raises(FileExistsError, match="--overwrite"):
        _write_jsonl(output, [{"replace": True}], overwrite=False)

    assert json.loads(output.read_text(encoding="utf-8")) == {"keep": True}
