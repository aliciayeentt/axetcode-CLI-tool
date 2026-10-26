from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from collections.abc import Callable
from typing import Iterator, Literal

Level = Literal["INFO", "WARN", "ERROR"]
_VALID_LEVELS: set[str] = {"INFO", "WARN", "ERROR"}


@dataclass(frozen=True)
class LogRecord:
    line_number: int
    timestamp: datetime
    timestamp_text: str
    level: Level
    message: str
    raw: str


@dataclass(frozen=True)
class ParseResult:
    records: Iterator[LogRecord]
    get_malformed_lines: Callable[[], int]


class LogParser:
    """Streaming parser for v1 log lines.

    Expected format:
    YYYY-MM-DD HH:MM:SS LEVEL Message text
    """

    def parse_file(self, file_path: str | Path) -> ParseResult:
        path = Path(file_path)
        malformed = 0

        def _iter_records() -> Iterator[LogRecord]:
            nonlocal malformed
            with path.open("r", encoding="utf-8", errors="strict") as fh:
                for line_number, raw_line in enumerate(fh, start=1):
                    line = raw_line.rstrip("\r\n")
                    record = self.parse_line(line=line, line_number=line_number)
                    if record is None:
                        malformed += 1
                        continue
                    yield record

        return ParseResult(records=_iter_records(), get_malformed_lines=lambda: malformed)

    def parse_line(self, line: str, line_number: int) -> LogRecord | None:
        if not line:
            return None

        parts = line.split(" ", 3)
        if len(parts) != 4:
            return None

        date_part, time_part, level_part, message = parts
        if level_part not in _VALID_LEVELS:
            return None
        if message == "":
            return None

        timestamp_text = f"{date_part} {time_part}"
        try:
            timestamp = datetime.strptime(timestamp_text, "%Y-%m-%d %H:%M:%S")
        except ValueError:
            return None

        return LogRecord(
            line_number=line_number,
            timestamp=timestamp,
            timestamp_text=timestamp_text,
            level=level_part,  # type: ignore[arg-type]
            message=message,
            raw=line,
        )


def iter_records_with_malformed_count(file_path: str | Path) -> tuple[Iterator[LogRecord], Callable[[], int]]:
    """Return a streaming iterator and a callback to retrieve malformed count.

    The malformed count is finalized after consuming the iterator.
    """
    parser = LogParser()
    parse_result = parser.parse_file(file_path)
    return parse_result.records, parse_result.get_malformed_lines
