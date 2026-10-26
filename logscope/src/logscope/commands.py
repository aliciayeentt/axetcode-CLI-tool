from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from pathlib import Path

from .parser import iter_records_with_malformed_count


@dataclass(frozen=True)
class SummaryResult:
    command: str
    file: str
    counts: dict[str, int]
    top_errors: list[dict[str, int | str]]
    first_timestamp: str | None
    last_timestamp: str | None
    valid_lines: int
    malformed_lines: int


def run_summary(file_path: str | Path) -> SummaryResult:
    records, get_malformed_lines = iter_records_with_malformed_count(file_path)

    level_counts: Counter[str] = Counter()
    error_counts: Counter[str] = Counter()
    valid_lines = 0
    first_timestamp = None
    last_timestamp = None

    for record in records:
        valid_lines += 1
        level_counts[record.level] += 1

        if first_timestamp is None or record.timestamp < first_timestamp:
            first_timestamp = record.timestamp
        if last_timestamp is None or record.timestamp > last_timestamp:
            last_timestamp = record.timestamp

        if record.level == "ERROR":
            error_counts[record.message] += 1

    top_errors = [
        {"message": message, "count": count}
        for message, count in sorted(error_counts.items(), key=lambda item: (-item[1], item[0]))[:5]
    ]

    return SummaryResult(
        command="summary",
        file=Path(file_path).name,
        counts={
            "INFO": level_counts.get("INFO", 0),
            "WARN": level_counts.get("WARN", 0),
            "ERROR": level_counts.get("ERROR", 0),
        },
        top_errors=top_errors,
        first_timestamp=first_timestamp.strftime("%Y-%m-%d %H:%M:%S") if first_timestamp else None,
        last_timestamp=last_timestamp.strftime("%Y-%m-%d %H:%M:%S") if last_timestamp else None,
        valid_lines=valid_lines,
        malformed_lines=get_malformed_lines(),
    )
