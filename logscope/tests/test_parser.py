from __future__ import annotations

from pathlib import Path

import pytest

from logscope.parser import LogParser


def test_parse_line_valid() -> None:
    parser = LogParser()
    rec = parser.parse_line(
        "2026-10-01 09:01:21 ERROR Database connection failed",
        line_number=3,
    )

    assert rec is not None
    assert rec.line_number == 3
    assert rec.timestamp_text == "2026-10-01 09:01:21"
    assert rec.level == "ERROR"
    assert rec.message == "Database connection failed"
    assert rec.raw == "2026-10-01 09:01:21 ERROR Database connection failed"


@pytest.mark.parametrize(
    "line",
    [
        "",
        "2026-10-01 09:01:21 DEBUG nope",
        "2026-99-01 09:01:21 ERROR bad date",
        "2026-10-01 09:01:21 ERROR",
        "2026-10-01 09:01 ERROR missing seconds",
    ],
)
def test_parse_line_malformed(line: str) -> None:
    parser = LogParser()
    assert parser.parse_line(line, line_number=1) is None


def test_parse_file_crlf_and_out_of_order(tmp_path: Path) -> None:
    file_path = tmp_path / "sample.log"
    file_path.write_text(
        "2026-10-01 09:18:12 ERROR Request timed out\r\n"
        "2026-10-01 08:59:58 INFO Application started\r\n"
        "bad line\r\n",
        encoding="utf-8",
    )

    parser = LogParser()
    result = parser.parse_file(file_path)
    records = list(result.records)

    assert [r.level for r in records] == ["ERROR", "INFO"]
    assert [r.line_number for r in records] == [1, 3]
    assert result.get_malformed_lines() == 1


def test_parse_file_invalid_utf8_raises_decode_error(tmp_path: Path) -> None:
    file_path = tmp_path / "invalid.log"
    file_path.write_bytes(b"2026-10-01 09:00:00 INFO ok\n\xff\n")

    parser = LogParser()
    result = parser.parse_file(file_path)

    with pytest.raises(UnicodeDecodeError):
        list(result.records)
