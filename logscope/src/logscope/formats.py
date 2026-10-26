from __future__ import annotations

import json
import sys
from dataclasses import asdict
from pathlib import Path
from typing import Literal, TextIO

from .commands import GrepResult, SummaryResult, TimelineResult

FormatType = Literal["text", "json", "md"]


def _default_md_path(input_file: str | Path, command: str) -> Path:
    stem = Path(input_file).stem
    return Path.cwd() / f"{stem}_{command}_report.md"


def _ensure_md_path(command: str, input_file: str | Path, output: str | None) -> Path:
    if output is None:
        path = _default_md_path(input_file, command)
    else:
        path = Path(output)

    if path.exists():
        raise ValueError(f"Output file already exists: {path}")

    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def _summary_to_text(result: SummaryResult) -> str:
    first = result.first_timestamp if result.first_timestamp is not None else "N/A"
    last = result.last_timestamp if result.last_timestamp is not None else "N/A"

    lines = [
        "Summary",
        f"INFO: {result.counts['INFO']} | WARN: {result.counts['WARN']} | ERROR: {result.counts['ERROR']}",
        f"First timestamp: {first}",
        f"Last timestamp: {last}",
        "Top errors:",
    ]

    if result.top_errors:
        for entry in result.top_errors:
            lines.append(f"- {entry['message']} ({entry['count']})")
    else:
        lines.append("- None")

    lines.append(f"Valid lines: {result.valid_lines} | Malformed lines: {result.malformed_lines}")
    return "\n".join(lines)


def _summary_to_md(result: SummaryResult) -> str:
    first = result.first_timestamp if result.first_timestamp is not None else "N/A"
    last = result.last_timestamp if result.last_timestamp is not None else "N/A"

    lines = [
        "# LogScope Summary Report",
        "",
        f"- File: `{result.file}`",
        "",
        "## Counts",
        "",
        f"- INFO: {result.counts['INFO']}",
        f"- WARN: {result.counts['WARN']}",
        f"- ERROR: {result.counts['ERROR']}",
        "",
        "## Time Range",
        "",
        f"- First timestamp: {first}",
        f"- Last timestamp: {last}",
        "",
        "## Top Errors",
        "",
    ]

    if result.top_errors:
        for entry in result.top_errors:
            lines.append(f"- {entry['message']} ({entry['count']})")
    else:
        lines.append("- None")

    lines.extend(
        [
            "",
            "## Parsing Stats",
            "",
            f"- Valid lines: {result.valid_lines}",
            f"- Malformed lines: {result.malformed_lines}",
            "",
        ]
    )

    return "\n".join(lines)


def _timeline_to_text(result: TimelineResult) -> str:
    lines = [f"Error timeline (bucket: {result.bucket})"]

    if result.buckets:
        for bucket in result.buckets:
            bar = "#" * bucket.error_count
            lines.append(f"{bucket.start} | {bar} {bucket.error_count}")
    else:
        lines.append("No errors found")

    lines.append(f"Valid lines: {result.valid_lines} | Malformed lines: {result.malformed_lines}")
    return "\n".join(lines)


def _timeline_to_md(result: TimelineResult) -> str:
    lines = [
        "# LogScope Timeline Report",
        "",
        f"- File: `{result.file}`",
        f"- Bucket: `{result.bucket}`",
        "",
        "## Error Buckets",
        "",
    ]

    if result.buckets:
        lines.append("| Bucket start | Error count |")
        lines.append("| --- | ---: |")
        for bucket in result.buckets:
            lines.append(f"| {bucket.start} | {bucket.error_count} |")
    else:
        lines.append("No errors found")

    lines.extend(
        [
            "",
            "## Parsing Stats",
            "",
            f"- Valid lines: {result.valid_lines}",
            f"- Malformed lines: {result.malformed_lines}",
            "",
        ]
    )

    return "\n".join(lines)


def _grep_to_text(result: GrepResult) -> int:
    for match in result.matches:
        print(match.raw)

    print(
        f"Matched lines: {result.matched_count} | Malformed lines: {result.malformed_lines}",
        file=sys.stderr,
    )
    return 0


def _grep_json_stream(result: GrepResult, stream: TextIO) -> None:
    stream.write("{")
    stream.write('"command":"grep",')
    stream.write(f'"file":{json.dumps(result.file)},')
    stream.write(f'"filters":{json.dumps(result.filters, separators=(",", ":"))},')
    stream.write('"matches":[')

    first = True
    matched_count = 0
    for match in result.matches:
        if not first:
            stream.write(",")
        stream.write(json.dumps(asdict(match), separators=(",", ":")))
        first = False
        matched_count += 1

    stream.write("],")
    stream.write(f'"matched_count":{matched_count},')
    stream.write(f'"valid_lines":{result.valid_lines},')
    stream.write(f'"malformed_lines":{result.malformed_lines}')
    stream.write("}\n")


def _grep_md_stream(result: GrepResult, path: Path) -> None:
    with path.open("w", encoding="utf-8", newline="\n") as fh:
        fh.write("# LogScope Grep Report\n\n")
        fh.write(f"- File: `{result.file}`\n")
        fh.write(f"- Level filter: `{result.filters['level']}`\n")
        fh.write(f"- Since filter: `{result.filters['since']}`\n\n")
        fh.write("## Matching Lines\n\n")
        fh.write("```text\n")
        matched_count = 0
        for match in result.matches:
            fh.write(match.raw)
            fh.write("\n")
            matched_count += 1
        fh.write("```\n\n")
        fh.write("## Parsing Stats\n\n")
        fh.write(f"- Matched lines: {matched_count}\n")
        fh.write(f"- Valid lines: {result.valid_lines}\n")
        fh.write(f"- Malformed lines: {result.malformed_lines}\n")


def emit_summary(result: SummaryResult, *, fmt: FormatType, output: str | None) -> int:
    if output is not None and fmt != "md":
        raise ValueError("--output is only valid with --format md")

    if fmt == "text":
        print(_summary_to_text(result))
        return 0

    if fmt == "json":
        payload = asdict(result)
        print(json.dumps(payload, separators=(",", ":")))
        return 0

    md_path = _ensure_md_path(result.command, result.file, output)
    md_path.write_text(_summary_to_md(result), encoding="utf-8", newline="\n")
    print(md_path)
    return 0


def emit_timeline(result: TimelineResult, *, fmt: FormatType, output: str | None) -> int:
    if output is not None and fmt != "md":
        raise ValueError("--output is only valid with --format md")

    if fmt == "text":
        print(_timeline_to_text(result))
        return 0

    if fmt == "json":
        payload = {
            "command": result.command,
            "file": result.file,
            "bucket": result.bucket,
            "buckets": [asdict(bucket) for bucket in result.buckets],
            "valid_lines": result.valid_lines,
            "malformed_lines": result.malformed_lines,
        }
        print(json.dumps(payload, separators=(",", ":")))
        return 0

    md_path = _ensure_md_path(result.command, result.file, output)
    md_path.write_text(_timeline_to_md(result), encoding="utf-8", newline="\n")
    print(md_path)
    return 0


def emit_grep(result: GrepResult, *, fmt: FormatType, output: str | None) -> int:
    if output is not None and fmt != "md":
        raise ValueError("--output is only valid with --format md")

    if fmt == "text":
        return _grep_to_text(result)

    if fmt == "json":
        _grep_json_stream(result, sys.stdout)
        return 0

    md_path = _ensure_md_path(result.command, result.file, output)
    _grep_md_stream(result, md_path)
    print(md_path)
    return 0
