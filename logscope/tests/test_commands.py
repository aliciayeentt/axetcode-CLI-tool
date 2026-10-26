from __future__ import annotations

from pathlib import Path

import pytest

from logscope.commands import run_summary, run_timeline


FIXTURES = Path(__file__).parent / "fixtures"


def test_run_summary_on_spec_sample() -> None:
    result = run_summary(FIXTURES / "sample.log")

    assert result.command == "summary"
    assert result.file == "sample.log"
    assert result.counts == {"INFO": 1, "WARN": 1, "ERROR": 3}
    assert result.top_errors == [
        {"message": "Database connection failed", "count": 2},
        {"message": "Request timed out", "count": 1},
    ]
    assert result.first_timestamp == "2026-10-01 08:59:58"
    assert result.last_timestamp == "2026-10-01 09:18:12"
    assert result.valid_lines == 5
    assert result.malformed_lines == 0


def test_run_summary_with_malformed_and_tie_breaking(tmp_path: Path) -> None:
    log_path = tmp_path / "tie.log"
    log_path.write_text(
        "2026-10-01 09:00:00 ERROR Zebra issue\n"
        "2026-10-01 09:00:01 ERROR Apple issue\n"
        "2026-10-01 09:00:02 ERROR Zebra issue\n"
        "2026-10-01 09:00:03 ERROR Apple issue\n"
        "bad line\n",
        encoding="utf-8",
    )

    result = run_summary(log_path)

    assert result.top_errors == [
        {"message": "Apple issue", "count": 2},
        {"message": "Zebra issue", "count": 2},
    ]
    assert result.valid_lines == 4
    assert result.malformed_lines == 1


def test_run_summary_empty_file(tmp_path: Path) -> None:
    log_path = tmp_path / "empty.log"
    log_path.write_text("", encoding="utf-8")

    result = run_summary(log_path)

    assert result.counts == {"INFO": 0, "WARN": 0, "ERROR": 0}
    assert result.top_errors == []
    assert result.first_timestamp is None
    assert result.last_timestamp is None
    assert result.valid_lines == 0
    assert result.malformed_lines == 0


def test_run_timeline_on_spec_sample_default_bucket() -> None:
    result = run_timeline(FIXTURES / "sample.log")

    assert result.command == "timeline"
    assert result.file == "sample.log"
    assert result.bucket == "15m"
    assert [(bucket.start, bucket.error_count) for bucket in result.buckets] == [
        ("2026-10-01 09:00:00", 2),
        ("2026-10-01 09:15:00", 1),
    ]
    assert result.valid_lines == 5
    assert result.malformed_lines == 0


def test_run_timeline_with_out_of_order_and_malformed(tmp_path: Path) -> None:
    log_path = tmp_path / "timeline.log"
    log_path.write_text(
        "2026-10-01 09:18:12 ERROR Request timed out\n"
        "2026-10-01 09:01:21 ERROR Database connection failed\n"
        "2026-10-01 09:00:05 WARN Retry attempt 1\n"
        "bad line\n",
        encoding="utf-8",
    )

    result = run_timeline(log_path, bucket="15m")

    assert [(bucket.start, bucket.error_count) for bucket in result.buckets] == [
        ("2026-10-01 09:00:00", 1),
        ("2026-10-01 09:15:00", 1),
    ]
    assert result.valid_lines == 3
    assert result.malformed_lines == 1


def test_run_timeline_no_errors(tmp_path: Path) -> None:
    log_path = tmp_path / "no-errors.log"
    log_path.write_text(
        "2026-10-01 08:59:58 INFO Application started\n"
        "2026-10-01 09:00:05 WARN Retry attempt 1\n",
        encoding="utf-8",
    )

    result = run_timeline(log_path)

    assert result.buckets == []
    assert result.valid_lines == 2
    assert result.malformed_lines == 0


@pytest.mark.parametrize("bucket", ["0m", "-1m", "1.5h", "15x", "m", ""])
def test_run_timeline_rejects_invalid_bucket(tmp_path: Path, bucket: str) -> None:
    log_path = tmp_path / "sample.log"
    log_path.write_text("2026-10-01 09:00:00 ERROR boom\n", encoding="utf-8")

    with pytest.raises(ValueError, match="Invalid bucket duration"):
        run_timeline(log_path, bucket=bucket)
