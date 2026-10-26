from __future__ import annotations

from pathlib import Path

from logscope.commands import run_summary


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
