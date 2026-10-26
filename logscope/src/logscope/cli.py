from __future__ import annotations

import argparse
import sys

from .commands import run_grep, run_summary, run_timeline
from .formats import emit_grep, emit_summary, emit_timeline


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="logscope")
    subparsers = parser.add_subparsers(dest="command", required=True)

    summary = subparsers.add_parser("summary")
    summary.add_argument("file")
    summary.add_argument("--format", choices=["json", "md"], default="text")
    summary.add_argument("--output")

    timeline = subparsers.add_parser("timeline")
    timeline.add_argument("file")
    timeline.add_argument("--bucket", default="15m")
    timeline.add_argument("--format", choices=["json", "md"], default="text")
    timeline.add_argument("--output")

    grep = subparsers.add_parser("grep")
    grep.add_argument("file")
    grep.add_argument("--level", choices=["INFO", "WARN", "ERROR"])
    grep.add_argument("--since")
    grep.add_argument("--format", choices=["json", "md"], default="text")
    grep.add_argument("--output")

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    try:
        if args.command == "summary":
            result = run_summary(args.file)
            return emit_summary(result, fmt=args.format, output=args.output)

        if args.command == "timeline":
            result = run_timeline(args.file, bucket=args.bucket)
            return emit_timeline(result, fmt=args.format, output=args.output)

        if args.command == "grep":
            result = run_grep(args.file, level=args.level, since=args.since)
            return emit_grep(result, fmt=args.format, output=args.output)

        parser.error("Unknown command")
        return 2
    except (OSError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
