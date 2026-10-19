"""Batch processing pipeline for the research telemetry datasets."""

from __future__ import annotations

import argparse
import json
import logging
from dataclasses import dataclass
from pathlib import Path

from .parsers import (
    NormalizedEvent,
    ParseResult,
    parse_keystroke_dataset,
    parse_mouse_dataset,
    build_keystroke_reference_index,
    validate_session,
)

LOGGER = logging.getLogger(__name__)
DEFAULT_INPUT_ROOT = Path("data/raw")
DEFAULT_OUTPUT_ROOT = Path("data/processed")


@dataclass
class ProcessingSummary:
    dataset: str
    files_discovered: int
    files_selected: int
    files_skipped: int
    files_skipped_reasons: dict[str, int]
    raw_lines_read: int
    metadata_lines_ignored: int
    candidate_events: int
    malformed_rows: int
    accepted_events: int
    deduplicated: int
    written_events: int
    unmatched_files: int
    ambiguous_files: int

    @property
    def discovered(self) -> int:
        return self.candidate_events

    @property
    def accepted(self) -> int:
        return self.accepted_events

    @property
    def rejected(self) -> int:
        return self.malformed_rows

    @property
    def written(self) -> int:
        return self.written_events


def _deduplicate(records: list[NormalizedEvent]) -> tuple[list[NormalizedEvent], int]:
    """Remove only repeated reads of the same physical source line."""

    unique: list[NormalizedEvent] = []
    seen: set[tuple[str, str, int]] = set()
    for record in records:
        key = (record.dataset, record.source_file, record.line_number)
        if key in seen:
            continue
        seen.add(key)
        unique.append(record)
    return unique, len(records) - len(unique)


def _sort_key(record: NormalizedEvent) -> tuple[int, str, int]:
    return record.timestamp, record.source_file, record.line_number


def write_jsonl(records: list[NormalizedEvent], output_path: Path) -> int:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    ordered_records = sorted(records, key=_sort_key)
    with output_path.open("w", encoding="utf-8", newline="\n") as output_file:
        for record in ordered_records:
            output_file.write(
                json.dumps(record.model_dump(exclude_none=True), allow_nan=False, sort_keys=True)
            )
            output_file.write("\n")
    return len(ordered_records)


def _process_result(
    dataset: str,
    result: ParseResult,
    output_path: Path,
) -> ProcessingSummary:
    deduplicated_records, deduplicated = _deduplicate(result.records)
    written = write_jsonl(deduplicated_records, output_path)
    stats = result.stats
    summary = ProcessingSummary(
        dataset=dataset,
        files_discovered=stats.files_discovered,
        files_selected=stats.files_selected,
        files_skipped=stats.files_skipped,
        files_skipped_reasons=dict(stats.files_skipped_reasons),
        raw_lines_read=stats.raw_lines_read,
        metadata_lines_ignored=stats.metadata_lines_ignored,
        candidate_events=stats.candidate_events,
        malformed_rows=stats.malformed_rows,
        accepted_events=stats.accepted_events,
        deduplicated=deduplicated,
        written_events=written,
        unmatched_files=stats.unmatched_files,
        ambiguous_files=stats.ambiguous_files,
    )
    LOGGER.info(
        "%s: files_discovered=%d files_selected=%d files_skipped=%d "
        "raw_lines=%d metadata_ignored=%d candidate_events=%d malformed_rows=%d "
        "accepted_events=%d deduplicated=%d written_events=%d",
        summary.dataset,
        summary.files_discovered,
        summary.files_selected,
        summary.files_skipped,
        summary.raw_lines_read,
        summary.metadata_lines_ignored,
        summary.candidate_events,
        summary.malformed_rows,
        summary.accepted_events,
        summary.deduplicated,
        summary.written_events,
    )
    return summary


def process_session(
    session: int = 0,
    input_root: Path = DEFAULT_INPUT_ROOT,
    output_root: Path = DEFAULT_OUTPUT_ROOT,
) -> list[ProcessingSummary]:
    """Process one session from both raw datasets and write deterministic JSONL."""

    validate_session(session)
    keystroke_root = input_root / "UB_keystroke_dataset"
    reference_index = build_keystroke_reference_index(keystroke_root)
    keystroke_result = parse_keystroke_dataset(keystroke_root, session=session)
    summaries = [
        _process_result(
            "keystroke",
            keystroke_result,
            output_root / f"keystroke_session{session}_processed.jsonl",
        )
    ]
    del keystroke_result

    mouse_result = parse_mouse_dataset(
        input_root / "UB_mouse_and_events_dataset",
        session=session,
        reference_index=reference_index,
    )
    summaries.append(
        _process_result(
            "mouse",
            mouse_result,
            output_root / f"mouse_session{session}_processed.jsonl",
        )
    )
    return summaries


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Process ZeroKey research telemetry. Mouse session selection uses "
            "unique exact-basename matches to documented keystroke files; "
            "mouse filename semantics remain unverified."
        )
    )
    parser.add_argument("--session", type=int, default=0, choices=(0, 1, 2))
    parser.add_argument("--input-root", type=Path, default=DEFAULT_INPUT_ROOT)
    parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT)
    parser.add_argument(
        "--log-level",
        default="INFO",
        choices=("DEBUG", "INFO", "WARNING", "ERROR"),
    )
    return parser


def main(arguments: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(arguments)
    logging.basicConfig(level=getattr(logging, args.log_level), format="%(levelname)s %(message)s")
    try:
        summaries = process_session(args.session, args.input_root, args.output_root)
    except (OSError, ValueError) as error:
        LOGGER.error("Pipeline failed: %s", error)
        return 1
    for summary in summaries:
        print(
            f"{summary.dataset}: files_discovered={summary.files_discovered} "
            f"files_selected={summary.files_selected} files_skipped={summary.files_skipped} "
            f"raw_lines={summary.raw_lines_read} "
            f"metadata_ignored={summary.metadata_lines_ignored} "
            f"candidate_events={summary.candidate_events} "
            f"malformed_rows={summary.malformed_rows} "
            f"accepted_events={summary.accepted_events} "
            f"deduplicated={summary.deduplicated} written_events={summary.written_events} "
            f"unmatched_files={summary.unmatched_files} "
            f"ambiguous_files={summary.ambiguous_files}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())