# LogScope — CLI Specification

**Version:** 1.0  
**Status:** Ready for implementation planning  
**Implementation language:** Python 3.11+ (preferred; standard-library runtime dependencies)  
**Interface:** Command-line application named `logscope`

## 1. Goal

Build a fast, dependable command-line tool for operations teams to inspect application logs after incidents **without opening a dashboard**. Users must be able to summarize a log, view errors over time, or filter individual log entries. The tool must process a log file of at least **100 MB without loading the entire file into memory**.

## 2. Supported input

### 2.1 Log-line format (v1)

Each valid line has this structure:

```text
YYYY-MM-DD HH:MM:SS LEVEL Message text
```

Examples:

```text
2026-10-01 08:59:58 INFO Application started
2026-10-01 09:00:05 WARN Retry attempt 1
2026-10-01 09:01:21 ERROR Database connection failed
2026-10-01 09:03:47 ERROR Database connection failed
2026-10-01 09:18:12 ERROR Request timed out
```

Parsing rules:

- Use UTF-8 text and handle files line by line. Do not assume chronological input order.
- Accept only the three **case-sensitive** levels: `INFO`, `WARN`, `ERROR`.
- Require a real date/time in `YYYY-MM-DD HH:MM:SS` format and a nonempty message.
- The timestamp is a **naive local timestamp**. Do not convert time zones; compare and display timestamps as written. All timestamps within a single file are assumed to use the same local time zone.
- The message consists of the remainder of the line after the level and its separating space. Trim the trailing newline, but preserve message content for exact grouping.
- Invalid timestamps, unknown levels, missing fields, blank lines, and undecodable UTF-8 lines are **malformed**. Count and skip them. A malformed line must **never crash** processing.
- A log file may have LF or CRLF line endings.

**Out of scope for v1:** multiline stack traces, JSON logs, alternate log formats, multiple log files per invocation, time-zone-aware input, and compressed files.

## 3. Command-line interface

```text
logscope summary <file> [--format json|md] [--output <path>]
logscope timeline <file> [--bucket <duration>] [--format json|md] [--output <path>]
logscope grep <file> [--level INFO|WARN|ERROR] [--since "YYYY-MM-DD HH:MM[:SS]"] [--format json|md] [--output <path>]
logscope --help
logscope <command> --help
```

Default format, if `--format` is not specified, is **human-readable terminal text**. The `--format` option must work for **all three commands**.

- `--format json`: write one valid JSON document to **stdout**, without extra explanatory text on stdout.
- `--format md`: write a Markdown report to a file. Default name: `<log-stem>_<command>_report.md` in the current directory (for example, `app_summary_report.md`). Print the created file path to stdout.
- `--output <path>`: optional custom output path, valid **only** with `--format md`. Do not silently overwrite an existing report: require the user to choose another path or explicitly remove the old file.
- Invalid CLI arguments, an invalid `--since` timestamp, an invalid bucket duration, unreadable/nonexistent input files, and output-write failures must produce clear messages on **stderr** and a nonzero exit code.
- A file with no valid entries is not a fatal error; produce an empty/zero-valued result and report the malformed count.

## 4. Command: `summary`

### Example

```bash
logscope summary app.log
logscope summary app.log --format json
logscope summary app.log --format md
```

### Required behavior

1. Count valid entries by level: `INFO`, `WARN`, and `ERROR` (show all three, including zeros).
2. Find the **top five most frequent exact error messages** from `ERROR` entries only, with their frequencies. Group by exact message text (case-sensitive), not by timestamp or full log line.
3. Report the **earliest and latest timestamps** among all valid entries, determined by timestamp value, not file position.
4. Include total valid line count and malformed line count.
5. Sort error messages by **descending frequency**, breaking ties by **ascending alphabetical message text**; return no more than five.
6. If there are no valid timestamps, show `N/A` in terminal/Markdown and `null` in JSON. If there are no errors, the top-errors collection is empty.

### JSON contract

```json
{
  "command": "summary",
  "file": "app.log",
  "counts": { "INFO": 1, "WARN": 1, "ERROR": 3 },
  "top_errors": [
    { "message": "Database connection failed", "count": 2 },
    { "message": "Request timed out", "count": 1 }
  ],
  "first_timestamp": "2026-10-01 08:59:58",
  "last_timestamp": "2026-10-01 09:18:12",
  "valid_lines": 5,
  "malformed_lines": 0
}
```

## 5. Command: `timeline`

### Example

```bash
logscope timeline app.log --bucket 15m
logscope timeline app.log --bucket 1h --format json
logscope timeline app.log --bucket 15m --format md
```

### Required behavior

1. Count **ERROR** entries per time bucket, based on their parsed timestamps.
2. `--bucket` defaults to `15m`. Accept a positive integer followed by `m` (minutes) or `h` (hours), such as `5m`, `15m`, `30m`, `1h`. Reject zero, negatives, decimals, and unsupported units.
3. For each date, bucket starts are aligned to local **midnight** (e.g. for `15m`, 09:00:00–09:14:59 belongs to the bucket beginning 09:00:00). Use inclusive start and exclusive end for the bucket interval.
4. Print buckets in ascending timestamp order, regardless of log order.
5. Show a **text-based bar chart** in terminal output. One `#` character represents one error; counts must also be printed numerically. For readability, bars may be scaled when needed, but never misrepresent the numeric count. A simple unscaled bar for small values is preferred.
6. Show only buckets containing at least one error (do not create potentially huge spans of zero-error buckets).
7. Include valid and malformed line counts in the terminal/Markdown report and JSON result.
8. If there are no errors, output a clear `No errors found` message (or an empty JSON `buckets` array).

### Sample terminal output

```text
Error timeline (bucket: 15m)
2026-10-01 09:00:00 | ## 2
2026-10-01 09:15:00 | # 1
Valid lines: 5 | Malformed lines: 0
```

### JSON contract

```json
{
  "command": "timeline",
  "file": "app.log",
  "bucket": "15m",
  "buckets": [
    { "start": "2026-10-01 09:00:00", "error_count": 2 },
    { "start": "2026-10-01 09:15:00", "error_count": 1 }
  ],
  "valid_lines": 5,
  "malformed_lines": 0
}
```

## 6. Command: `grep`

### Example

```bash
logscope grep app.log --level ERROR --since "2026-10-01 09:00"
logscope grep app.log --level WARN --format json
logscope grep app.log --since "2026-10-01 09:00" --format md
```

### Required behavior

1. Output log lines matching the requested filters. Both filters are optional; when omitted, return all valid lines.
2. `--level` accepts `INFO`, `WARN`, or `ERROR` only; filter by exact level.
3. `--since` accepts `YYYY-MM-DD HH:MM` or `YYYY-MM-DD HH:MM:SS`. A value without seconds means `:00`. Include entries whose timestamp is **greater than or equal to** the specified time.
4. When both filters are supplied, apply **AND** logic.
5. Preserve **original file order**, not sorted timestamp order.
6. In normal terminal format, print original matching lines to stdout. Print counts of matches and malformed lines to **stderr** so piped stdout contains only the matches.
7. For JSON, include matches with parsed fields and original line number; output must remain valid JSON even for large numbers of matches. **Stream JSON matches incrementally** instead of collecting all matches in memory.
8. For Markdown, write a report containing filter parameters, matching lines in a fenced text block, and counts. Stream matching lines to the output file.
9. If no lines match, return an empty result rather than an error.

### JSON contract

```json
{
  "command": "grep",
  "file": "app.log",
  "filters": { "level": "ERROR", "since": "2026-10-01 09:00:00" },
  "matches": [
    {
      "line_number": 3,
      "timestamp": "2026-10-01 09:01:21",
      "level": "ERROR",
      "message": "Database connection failed",
      "raw": "2026-10-01 09:01:21 ERROR Database connection failed"
    },
    {
      "line_number": 4,
      "timestamp": "2026-10-01 09:03:47",
      "level": "ERROR",
      "message": "Database connection failed",
      "raw": "2026-10-01 09:03:47 ERROR Database connection failed"
    },
    {
      "line_number": 5,
      "timestamp": "2026-10-01 09:18:12",
      "level": "ERROR",
      "message": "Request timed out",
      "raw": "2026-10-01 09:18:12 ERROR Request timed out"
    }
  ],
  "matched_count": 3,
  "valid_lines": 5,
  "malformed_lines": 0
}
```

The above illustrates structure; the number of `matches` in a real file depends on the filters. JSON may be constructed incrementally as long as its final structure is valid.

## 7. Performance and reliability

- Process input as a **stream** (e.g. iterate over the file one line at a time). **Never use `read()` or `readlines()` to load the whole log into memory.**
- Support logs of at least **100 MB**; memory should not grow just because there are more raw lines. Store only summary aggregates and use temporary disk-backed aggregation (for example, `sqlite3`) where necessary for a very high number of unique error messages or time buckets.
- For `grep`, stream matches to terminal, JSON, or Markdown output as they are found.
- Track malformed counts for every command; exclude malformed lines from all other calculations.
- Handle a malformed line without terminating parsing of subsequent lines.
- Process file read errors and failed report writes gracefully. Close file handles and remove temporary files, including on failure.
- Avoid additional runtime dependencies unless a clear reason is documented.

## 8. Expected deliverables

The implementation phase (after approval of the plan) should produce:

- An installable Python CLI with the `logscope` command as an entry point.
- Source code with a reusable log parser and command modules/functions.
- Automated tests (unit and CLI/integration tests).
- A `README.md` covering installation, sample usage, output formats, and limitations.
- A small `tests/fixtures/` sample log containing valid, duplicated-error, out-of-order, and malformed lines.
- A test or reproducible script generating and processing a 100 MB log file without reading it entirely into RAM.

**Suggested structure (may be refined during planning):**

```text
logscope/
├── SPEC.md
├── AGENTS.md
├── README.md
├── pyproject.toml
├── src/
│   └── logscope/
│       ├── __init__.py
│       ├── cli.py
│       ├── parser.py
│       ├── commands.py
│       └── formats.py
└── tests/
    ├── fixtures/
    │   └── sample.log
    ├── test_parser.py
    ├── test_commands.py
    └── test_cli.py
```

## 9. Acceptance criteria / test cases

The implementation is accepted only if all the following hold:

| ID | Test | Expected outcome |
| --- | --- | --- |
| A1 | Run `summary` on the sample in §2.1 | INFO = 1, WARN = 1, ERROR = 3; repeated database error count = 2; earliest = 08:59:58; latest = 09:18:12. |
| A2 | Run `timeline --bucket 15m` on the same sample | 09:00 bucket = 2, 09:15 bucket = 1. |
| A3 | Run `grep --level ERROR --since "2026-10-01 09:00"` | Three ERROR lines in original order; excludes INFO and WARN. |
| A4 | Append malformed entries, including a blank line, invalid date, unknown level, and missing message | Command completes; malformed count increases appropriately; valid results unchanged. |
| A5 | Input log is out of chronological order | Summary min/max and timeline order use timestamps; grep retains file order. |
| A6 | All commands with `--format json` | Valid parseable JSON with the documented fields and no stray stdout text. |
| A7 | All commands with `--format md` | A readable `.md` report file is created with appropriate results, filters (where applicable), and malformed count. |
| A8 | Empty file or file containing only malformed lines | No crash; counts zero, no matches/buckets, null timestamps where appropriate. |
| A9 | Missing file, invalid `--since`, `--bucket 0m`, invalid level, or unwritable output path | Clear stderr message and nonzero exit code. |
| A10 | At least 100 MB synthetic log, including a large number of matching lines | Completes without loading the whole file; `grep` output is streamed. |
| A11 | Error-message frequency ties | Top errors are deterministically ordered by count descending, then message ascending. |
| A12 | Input contains CRLF endings and invalid UTF-8 bytes | CRLF valid lines parse; invalid byte lines count as malformed and do not stop processing. |

## 10. Definition of done

- CLI matches this specification and all three commands work.
- Automated tests pass; 100 MB streaming behavior is demonstrated.
- Help output documents all options.
- README shows how to install and run the tool.
- **Before any coding begins, the coding assistant must submit an implementation plan for review and approval.** See `AGENTS.md`.
