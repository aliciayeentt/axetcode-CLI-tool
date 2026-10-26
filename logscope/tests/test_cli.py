from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "tests" / "fixtures"


def _run_cli(*args: str, cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", "logscope.cli", *args],
        cwd=cwd if cwd is not None else ROOT,
        text=True,
        capture_output=True,
    )


def test_summary_json_output() -> None:
    result = _run_cli("summary", str(FIXTURES / "sample.log"), "--format", "json")

    assert result.returncode == 0
    payload = json.loads(result.stdout)
    assert payload["command"] == "summary"
    assert payload["counts"] == {"INFO": 1, "WARN": 1, "ERROR": 3}
    assert result.stderr == ""


def test_timeline_json_output() -> None:
    result = _run_cli(
        "timeline",
        str(FIXTURES / "sample.log"),
        "--bucket",
        "15m",
        "--format",
        "json",
    )

    assert result.returncode == 0
    payload = json.loads(result.stdout)
    assert payload["command"] == "timeline"
    assert payload["bucket"] == "15m"
    assert payload["buckets"] == [
        {"start": "2026-10-01 09:00:00", "error_count": 2},
        {"start": "2026-10-01 09:15:00", "error_count": 1},
    ]


def test_grep_json_output() -> None:
    result = _run_cli(
        "grep",
        str(FIXTURES / "sample.log"),
        "--level",
        "ERROR",
        "--since",
        "2026-10-01 09:00",
        "--format",
        "json",
    )

    assert result.returncode == 0
    payload = json.loads(result.stdout)
    assert payload["command"] == "grep"
    assert payload["matched_count"] == 3
    assert [item["line_number"] for item in payload["matches"]] == [3, 4, 5]


def test_summary_md_default_output_path(tmp_path: Path) -> None:
    log_path = tmp_path / "app.log"
    log_path.write_text("2026-10-01 08:59:58 INFO Application started\n", encoding="utf-8")

    result = _run_cli("summary", str(log_path), "--format", "md", cwd=tmp_path)

    assert result.returncode == 0
    output_path = Path(result.stdout.strip())
    assert output_path.name == "app_summary_report.md"
    assert output_path.exists()


def test_grep_md_custom_output_path(tmp_path: Path) -> None:
    out_file = tmp_path / "report.md"

    result = _run_cli(
        "grep",
        str(FIXTURES / "sample.log"),
        "--level",
        "ERROR",
        "--format",
        "md",
        "--output",
        str(out_file),
    )

    assert result.returncode == 0
    assert out_file.exists()
    content = out_file.read_text(encoding="utf-8")
    assert "# LogScope Grep Report" in content
    assert "Database connection failed" in content


def test_reject_output_without_md_format() -> None:
    result = _run_cli(
        "summary",
        str(FIXTURES / "sample.log"),
        "--format",
        "json",
        "--output",
        "x.md",
    )

    assert result.returncode != 0
    assert "--output is only valid with --format md" in result.stderr


def test_refuse_overwrite_md_output(tmp_path: Path) -> None:
    log_path = tmp_path / "app.log"
    log_path.write_text("2026-10-01 08:59:58 INFO Application started\n", encoding="utf-8")

    out_file = tmp_path / "report.md"
    out_file.write_text("existing", encoding="utf-8")

    result = _run_cli(
        "summary",
        str(log_path),
        "--format",
        "md",
        "--output",
        str(out_file),
        cwd=tmp_path,
    )

    assert result.returncode != 0
    assert "Output file already exists" in result.stderr


def test_grep_text_writes_counts_to_stderr() -> None:
    result = _run_cli("grep", str(FIXTURES / "sample.log"), "--level", "ERROR")

    assert result.returncode == 0
    assert "ERROR Database connection failed" in result.stdout
    assert "Matched lines: 3 | Malformed lines: 0" in result.stderr
