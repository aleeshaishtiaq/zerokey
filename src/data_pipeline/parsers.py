"""Parsers for the research keystroke and mouse datasets."""

from __future__ import annotations

import logging
import re
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

LOGGER = logging.getLogger(__name__)
SUPPORTED_SESSIONS = (0, 1, 2)
KEYSTROKE_FILE_PATTERN = re.compile(r"^[0-9]{6}\.txt$")
MOUSE_FILE_PATTERN = re.compile(r"^[0-9]{6}\.txt$")
MOUSE_COORDINATE_PATTERN = re.compile(
    r"^\s*(?P<timestamp>\d+)\s*\|.*?\|\s*Mouse Coordinates\s*\|\s*"
    r"(?P<x>-?\d+)\s*,\s*(?P<y>-?\d+)\s*$"
)


class KeystrokeReference(BaseModel):
    model_config = ConfigDict(extra="forbid")

    source_file: str
    subject_id: str = Field(pattern=r"^[0-9]{3}$")
    session: int = Field(ge=0, le=2)
    keyboard_code: int = Field(ge=0, le=3)
    task_id: int = Field(ge=0, le=1)
    subset: Literal["baseline", "rotation"]
    mapping_basis: Literal["unique_exact_basename_match"]


class NormalizedEvent(BaseModel):
    """A validated, source-preserving event from either research dataset."""

    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)

    dataset: Literal["keystroke", "mouse"]
    subject_id: str = Field(pattern=r"^[0-9]{3}$")
    session: int = Field(ge=0, le=2)
    condition: Literal["baseline", "rotation", "unverified"]
    filename_suffix: str = Field(pattern=r"^[0-9]{3}$")
    original_filename: str = Field(pattern=r"^[0-9]{6}\.txt$")
    observed_session_digit: int = Field(ge=0, le=2)
    event_type: str = Field(min_length=1)
    timestamp: int = Field(ge=0)
    source_file: str = Field(min_length=1)
    line_number: int = Field(ge=1)
    keyboard_code: int | None = Field(default=None, ge=0, le=3)
    task_id: int | None = Field(default=None, ge=0, le=1)
    keystroke_reference: KeystrokeReference | None = None
    key: str | None = None
    action: str | None = None
    x: int | None = None
    y: int | None = None


@dataclass
class ParseIssue:
    source_file: str
    line_number: int | None
    reason: str


@dataclass
class ParseStats:
    files_discovered: int = 0
    files_selected: int = 0
    files_skipped: int = 0
    files_skipped_reasons: Counter[str] = field(default_factory=Counter)
    raw_lines_read: int = 0
    metadata_lines_ignored: int = 0
    candidate_events: int = 0
    malformed_rows: int = 0
    accepted_events: int = 0
    unmatched_files: int = 0
    ambiguous_files: int = 0


@dataclass
class ParseResult:
    records: list[NormalizedEvent] = field(default_factory=list)
    issues: list[ParseIssue] = field(default_factory=list)
    stats: ParseStats = field(default_factory=ParseStats)


@dataclass
class ReferenceIndex:
    references: dict[str, list[KeystrokeReference]]
    stats: ParseStats
    issues: list[ParseIssue] = field(default_factory=list)


def validate_session(session: int) -> int:
    if session not in SUPPORTED_SESSIONS:
        raise ValueError(f"Unsupported session {session}; choose one of {SUPPORTED_SESSIONS}.")
    return session


def _issue(result: ParseResult, path: Path, line_number: int | None, reason: str) -> None:
    issue = ParseIssue(str(path), line_number, reason)
    result.issues.append(issue)
    result.stats.malformed_rows += 1
    LOGGER.warning("Skipping %s line %s: %s", path, line_number or "?", reason)


def _skip_file(stats: ParseStats, reason: str, path: Path) -> None:
    stats.files_skipped += 1
    stats.files_skipped_reasons[reason] += 1
    LOGGER.warning("Skipping file %s: %s", path, reason)


def _keystroke_paths(root: Path, session: int | None) -> list[Path]:
    sessions = (session,) if session is not None else SUPPORTED_SESSIONS
    paths: list[Path] = []
    for current_session in sessions:
        session_root = root / f"s{current_session}"
        for subset in ("baseline", "rotation"):
            paths.extend(sorted((session_root / subset).glob("*.txt")))
    return paths


def _keystroke_metadata(path: Path) -> tuple[int, int, int, str] | None:
    if not KEYSTROKE_FILE_PATTERN.fullmatch(path.name):
        return None
    try:
        filename_session = int(path.stem[3])
        keyboard_code = int(path.stem[4])
        task_id = int(path.stem[5])
        parent_session = int(path.parent.parent.name[1:])
    except (IndexError, ValueError):
        return None
    subset = path.parent.name
    if (
        filename_session not in SUPPORTED_SESSIONS
        or keyboard_code not in range(4)
        or task_id not in (0, 1)
        or parent_session != filename_session
        or subset not in {"baseline", "rotation"}
    ):
        return None
    return filename_session, keyboard_code, task_id, subset


def _reference_from_path(path: Path) -> KeystrokeReference | None:
    metadata = _keystroke_metadata(path)
    if metadata is None:
        return None
    session, keyboard_code, task_id, subset = metadata
    return KeystrokeReference(
        source_file=path.as_posix(),
        subject_id=path.stem[:3],
        session=session,
        keyboard_code=keyboard_code,
        task_id=task_id,
        subset=subset,
        mapping_basis="unique_exact_basename_match",
    )


def build_keystroke_reference_index(root: Path) -> ReferenceIndex:
    """Index valid keystroke files by exact basename across all sessions."""

    if not root.exists():
        raise FileNotFoundError(f"Keystroke reference dataset is unavailable: {root}")
    stats = ParseStats()
    references: dict[str, list[KeystrokeReference]] = defaultdict(list)
    issues: list[ParseIssue] = []
    paths = _keystroke_paths(root, None)
    stats.files_discovered = len(paths)
    for path in paths:
        reference = _reference_from_path(path)
        if reference is None:
            stats.files_skipped += 1
            stats.files_skipped_reasons["invalid_or_mismatched_filename"] += 1
            issues.append(ParseIssue(str(path), None, "invalid or mismatched keystroke filename"))
            continue
        references[path.name].append(reference)
        stats.files_selected += 1
    if not references:
        raise ValueError(f"No valid keystroke reference files found under {root}")
    return ReferenceIndex(dict(references), stats, issues)


def parse_keystroke_dataset(root: Path, session: int = 0) -> ParseResult:
    """Parse one session, deriving subset from its actual directory."""

    validate_session(session)
    result = ParseResult()
    paths = _keystroke_paths(root, session)
    result.stats.files_discovered = len(paths)
    for path in paths:
        metadata = _keystroke_metadata(path)
        if metadata is None:
            _skip_file(result.stats, "invalid_or_mismatched_filename", path)
            continue
        filename_session, keyboard_code, task_id, subset = metadata
        result.stats.files_selected += 1
        try:
            lines = path.read_text(encoding="utf-8").splitlines()
        except OSError as error:
            _skip_file(result.stats, "unreadable_file", path)
            _issue(result, path, None, f"unreadable file: {error}")
            continue
        result.stats.raw_lines_read += len(lines)
        for line_number, line in enumerate(lines, start=1):
            if not line.strip():
                result.stats.metadata_lines_ignored += 1
                continue
            result.stats.candidate_events += 1
            parts = line.split()
            if len(parts) != 3:
                _issue(result, path, line_number, "expected key, action, timestamp_ms")
                continue
            key, action, timestamp_text = parts
            if action not in {"KeyDown", "KeyUp"}:
                _issue(result, path, line_number, f"unexpected action {action!r}")
                continue
            try:
                record = NormalizedEvent(
                    dataset="keystroke",
                    subject_id=path.stem[:3],
                    session=filename_session,
                    condition=subset,
                    filename_suffix=path.stem[3:],
                    original_filename=path.name,
                    observed_session_digit=filename_session,
                    event_type="keyboard",
                    timestamp=int(timestamp_text),
                    source_file=path.as_posix(),
                    line_number=line_number,
                    keyboard_code=keyboard_code,
                    task_id=task_id,
                    key=key,
                    action=action,
                )
            except (TypeError, ValueError) as error:
                _issue(result, path, line_number, f"invalid keystroke record: {error}")
                continue
            result.records.append(record)
            result.stats.accepted_events += 1
    return result


def _mouse_paths(root: Path) -> list[Path]:
    if not root.exists():
        raise FileNotFoundError(f"Mouse dataset is unavailable: {root}")
    return sorted(root.glob("*.txt"))


def parse_mouse_dataset(
    root: Path,
    session: int = 0,
    reference_index: ReferenceIndex | None = None,
) -> ParseResult:
    """Parse mouse events selected through unique keystroke references."""

    validate_session(session)
    if reference_index is None:
        reference_index = build_keystroke_reference_index(root.parent / "UB_keystroke_dataset")
    result = ParseResult()
    paths = _mouse_paths(root)
    result.stats.files_discovered = len(paths)
    for path in paths:
        if not MOUSE_FILE_PATTERN.fullmatch(path.name):
            _skip_file(result.stats, "invalid_mouse_filename", path)
            continue
        references = reference_index.references.get(path.name, [])
        if not references:
            result.stats.unmatched_files += 1
            _skip_file(result.stats, "unmatched_keystroke_reference", path)
            continue
        if len(references) > 1:
            result.stats.ambiguous_files += 1
            _skip_file(result.stats, "ambiguous_keystroke_reference", path)
            continue
        reference = references[0]
        if reference.session != session:
            _skip_file(result.stats, "reference_session_not_requested", path)
            continue
        result.stats.files_selected += 1
        try:
            lines = path.read_text(encoding="utf-8").splitlines()
        except OSError as error:
            _skip_file(result.stats, "unreadable_file", path)
            _issue(result, path, None, f"unreadable file: {error}")
            continue
        result.stats.raw_lines_read += len(lines)
        for line_number, line in enumerate(lines, start=1):
            if "Mouse Coordinates" not in line:
                result.stats.metadata_lines_ignored += 1
                continue
            result.stats.candidate_events += 1
            match = MOUSE_COORDINATE_PATTERN.match(line)
            if not match:
                _issue(result, path, line_number, "invalid mouse-coordinate record")
                continue
            try:
                record = NormalizedEvent(
                    dataset="mouse",
                    subject_id=reference.subject_id,
                    session=reference.session,
                    condition="unverified",
                    filename_suffix=path.stem[3:],
                    original_filename=path.name,
                    observed_session_digit=int(path.stem[3]),
                    event_type="mouse_move",
                    timestamp=int(match.group("timestamp")),
                    source_file=path.as_posix(),
                    line_number=line_number,
                    keystroke_reference=reference,
                    x=int(match.group("x")),
                    y=int(match.group("y")),
                )
            except (TypeError, ValueError) as error:
                _issue(result, path, line_number, f"invalid mouse record: {error}")
                continue
            result.records.append(record)
            result.stats.accepted_events += 1
    return result
