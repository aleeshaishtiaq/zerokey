import json
from pathlib import Path

import pytest

from src.data_pipeline.parsers import (
    build_keystroke_reference_index,
    parse_keystroke_dataset,
    parse_mouse_dataset,
)
from src.data_pipeline.pipeline import process_session
from src.data_pipeline.pipeline import _deduplicate


def write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def make_input_root(tmp_path: Path) -> Path:
    write(
        tmp_path / "UB_keystroke_dataset" / "s0" / "baseline" / "001000.txt",
        "LMenu KeyDown 10\nTab KeyUp 20\nmalformed\n",
    )
    write(
        tmp_path / "UB_keystroke_dataset" / "s0" / "rotation" / "001001.txt",
        "A KeyDown 30\nA KeyDown 30\n",
    )
    write(
        tmp_path / "UB_keystroke_dataset" / "s1" / "baseline" / "001100.txt",
        "B KeyDown 40\n",
    )
    write(
        tmp_path / "UB_keystroke_dataset" / "s2" / "rotation" / "001201.txt",
        "C KeyDown 50\n",
    )
    write(
        tmp_path / "UB_mouse_and_events_dataset" / "001000.txt",
        "header\n10 | date | Mouse Coordinates | 1,2\n",
    )
    write(
        tmp_path / "UB_mouse_and_events_dataset" / "001001.txt",
        "20 | date | Mouse Coordinates | 3,4\ninvalid Mouse Coordinates row\n",
    )
    write(
        tmp_path / "UB_mouse_and_events_dataset" / "001100.txt",
        "30 | date | Mouse Coordinates | 5,6\n",
    )
    write(
        tmp_path / "UB_mouse_and_events_dataset" / "001200.txt",
        "40 | date | Mouse Coordinates | 7,8\n",
    )
    return tmp_path


def test_keystroke_session_zero_reads_both_conditions_and_skips_bad_rows(tmp_path):
    result = parse_keystroke_dataset(make_input_root(tmp_path) / "UB_keystroke_dataset")

    assert [(record.condition, record.key) for record in result.records] == [
        ("baseline", "LMenu"),
        ("baseline", "Tab"),
        ("rotation", "A"),
        ("rotation", "A"),
    ]
    assert len(result.issues) == 1
    assert result.issues[0].line_number == 3
    assert all(record.session == 0 for record in result.records)
    assert all("/s1/" not in record.source_file for record in result.records)
    assert all("/s2/" not in record.source_file for record in result.records)


def test_mouse_session_zero_selects_only_supported_session_zero_files(tmp_path, caplog):
    input_root = make_input_root(tmp_path)
    write(
        input_root / "UB_mouse_and_events_dataset" / "001002.txt",
        "50 | date | Mouse Coordinates | 9,10\n",
    )
    result = parse_mouse_dataset(input_root / "UB_mouse_and_events_dataset")

    assert [(record.source_file, record.condition, record.filename_suffix) for record in result.records] == [
        ((tmp_path / "UB_mouse_and_events_dataset" / "001000.txt").as_posix(), "unverified", "000"),
        ((tmp_path / "UB_mouse_and_events_dataset" / "001001.txt").as_posix(), "unverified", "001"),
    ]
    assert len(result.issues) == 1
    assert result.issues[0].line_number == 2
    assert all(record.session == 0 for record in result.records)
    assert all("001100.txt" not in record.source_file for record in result.records)
    assert all("001200.txt" not in record.source_file for record in result.records)
    assert "unmatched_keystroke_reference" in caplog.text
    assert result.stats.unmatched_files == 2
    assert result.stats.files_selected == 2


def test_pipeline_writes_deterministic_session_zero_jsonl(tmp_path):
    input_root = make_input_root(tmp_path / "input")
    output_root = tmp_path / "output"

    summaries = process_session(0, input_root, output_root)

    assert [summary.dataset for summary in summaries] == ["keystroke", "mouse"]
    assert summaries[0].deduplicated == 0
    assert summaries[0].written == 4
    assert summaries[0].files_discovered == 2
    assert summaries[0].candidate_events == 5
    assert summaries[0].malformed_rows == 1
    assert summaries[0].accepted_events == 4
    assert summaries[1].files_discovered == 4
    assert summaries[1].files_selected == 2
    assert summaries[1].metadata_lines_ignored == 1
    assert summaries[1].candidate_events == 3
    assert summaries[1].malformed_rows == 1
    assert summaries[1].accepted_events == 2
    assert summaries[1].unmatched_files == 1
    assert summaries[1].written_events == 2
    output_path = output_root / "mouse_session0_processed.jsonl"
    lines = output_path.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 2
    assert all(json.loads(line)["session"] == 0 for line in lines)


def test_keystroke_readme_filename_metadata_is_extracted(tmp_path):
    path = tmp_path / "s1" / "rotation" / "123121.txt"
    write(path, "A KeyDown 63578429792961\n")

    result = parse_keystroke_dataset(tmp_path, session=1)
    record = result.records[0]

    assert record.subject_id == "123"
    assert record.session == 1
    assert record.keyboard_code == 2
    assert record.task_id == 1
    assert record.condition == "rotation"
    assert record.timestamp == 63578429792961


def test_keystroke_filename_session_must_match_parent_directory(tmp_path):
    path = tmp_path / "s0" / "baseline" / "123100.txt"
    write(path, "A KeyDown 10\n")

    result = parse_keystroke_dataset(tmp_path, session=0)

    assert result.records == []
    assert result.stats.files_skipped == 1
    assert result.stats.files_skipped_reasons["invalid_or_mismatched_filename"] == 1


def test_mouse_records_include_unique_keystroke_reference_and_raw_timestamp(tmp_path):
    input_root = make_input_root(tmp_path)

    result = parse_mouse_dataset(input_root / "UB_mouse_and_events_dataset")
    record = result.records[0]

    assert record.original_filename == "001000.txt"
    assert record.filename_suffix == "000"
    assert record.condition == "unverified"
    assert record.timestamp == 10
    assert record.keystroke_reference is not None
    assert record.keystroke_reference.subject_id == "001"
    assert record.keystroke_reference.session == 0
    assert record.keystroke_reference.keyboard_code == 0
    assert record.keystroke_reference.task_id == 0
    assert record.keystroke_reference.subset == "baseline"
    assert record.keystroke_reference.mapping_basis == "unique_exact_basename_match"


def test_mouse_ambiguous_reference_is_skipped(tmp_path):
    key_root = tmp_path / "UB_keystroke_dataset"
    write(key_root / "s0" / "baseline" / "001000.txt", "A KeyDown 1\n")
    write(key_root / "s0" / "rotation" / "001000.txt", "A KeyDown 1\n")
    mouse_root = tmp_path / "UB_mouse_and_events_dataset"
    write(mouse_root / "001000.txt", "10 | date | Mouse Coordinates | 1,2\n")

    index = build_keystroke_reference_index(key_root)
    result = parse_mouse_dataset(mouse_root, reference_index=index)

    assert result.records == []
    assert result.stats.ambiguous_files == 1
    assert result.stats.files_skipped_reasons["ambiguous_keystroke_reference"] == 1


def test_pipeline_rejects_invalid_session(tmp_path):
    with pytest.raises(ValueError, match="Unsupported session"):
        process_session(3, tmp_path, tmp_path / "output")


def test_duplicate_source_records_are_removed_without_collapsing_repeated_events(tmp_path):
    result = parse_mouse_dataset(make_input_root(tmp_path) / "UB_mouse_and_events_dataset")
    duplicate_records = [result.records[0], result.records[0], result.records[1]]

    unique, deduplicated = _deduplicate(duplicate_records)

    assert len(unique) == 2
    assert deduplicated == 1


def test_pipeline_output_has_no_nonstandard_json_values(tmp_path):
    input_root = make_input_root(tmp_path / "input")
    output_root = tmp_path / "output"
    process_session(0, input_root, output_root)

    for path in output_root.glob("*.jsonl"):
        for line in path.read_text(encoding="utf-8").splitlines():
            assert "NaN" not in line
            assert "Infinity" not in line
            json.loads(line)