from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timedelta
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


@dataclass(frozen=True)
class TimelineBucket:
    start: str
    error_count: int


@dataclass(frozen=True)
class TimelineResult:
    command: str
    file: str
    bucket: str
    buckets: list[TimelineBucket]
    valid_lines: int
    malformed_lines: int


def _parse_bucket(bucket: str) -> timedelta:
    if len(bucket) < 2:
        raise ValueError("Invalid bucket duration")

    unit = bucket[-1]
    value_text = bucket[:-1]
    if unit not in {"m", "h"} or not value_text.isdigit():
        raise ValueError("Invalid bucket duration")

    value = int(value_text)
    if value <= 0:
        raise ValueError("Invalid bucket duration")

    if unit == "m":
        return timedelta(minutes=value)
    return timedelta(hours=value)


def _bucket_start(timestamp: datetime, bucket_delta: timedelta) -> datetime:
    midnight = datetime(timestamp.year, timestamp.month, timestamp.day)
    seconds_since_midnight = int((timestamp - midnight).total_seconds())
    bucket_seconds = int(bucket_delta.total_seconds())
    aligned_seconds = (seconds_since_midnight // bucket_seconds) * bucket_seconds
    return midnight + timedelta(seconds=aligned_seconds)


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


def run_timeline(file_path: str | Path, bucket: str = "15m") -> TimelineResult:
    bucket_delta = _parse_bucket(bucket)
    records, get_malformed_lines = iter_records_with_malformed_count(file_path)

    bucket_counts: Counter[datetime] = Counter()
    valid_lines = 0

    for record in records:
        valid_lines += 1
        if record.level != "ERROR":
            continue

        bucket_start = _bucket_start(record.timestamp, bucket_delta)
        bucket_counts[bucket_start] += 1

    timeline_buckets = [
        TimelineBucket(start=start.strftime("%Y-%m-%d %H:%M:%S"), error_count=count)
        for start, count in sorted(bucket_counts.items(), key=lambda item: item[0])
    ]

    return TimelineResult(
        command="timeline",
        file=Path(file_path).name,
        bucket=bucket,
        buckets=timeline_buckets,
        valid_lines=valid_lines,
        malformed_lines=get_malformed_lines(),
    )
