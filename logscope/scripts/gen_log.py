from __future__ import annotations

import argparse
import random
from datetime import datetime, timedelta
from pathlib import Path


def _line_for(index: int, base: datetime) -> str:
    ts = base + timedelta(seconds=index % 172800)

    if index % 10 == 0:
        level = "ERROR"
        message = f"Database connection failed shard={index % 17}"
    elif index % 6 == 0:
        level = "WARN"
        message = f"Retry attempt {index % 5}"
    else:
        level = "INFO"
        message = f"Request completed path=/api/{index % 31} status=200"

    return f"{ts:%Y-%m-%d %H:%M:%S} {level} {message}\n"


def generate_log(output_path: Path, target_bytes: int, seed: int) -> tuple[int, int]:
    random.seed(seed)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    base = datetime(2026, 10, 1, 0, 0, 0)
    bytes_written = 0
    lines_written = 0

    with output_path.open("w", encoding="utf-8", newline="\n") as fh:
        while bytes_written < target_bytes:
            line = _line_for(lines_written, base)

            if lines_written % 2000 == 0:
                line = "malformed line without timestamp\n"
            elif lines_written % 5000 == 0:
                line = f"2026-10-32 00:00:00 INFO impossible date {lines_written}\n"

            fh.write(line)
            bytes_written += len(line.encode("utf-8"))
            lines_written += 1

    return lines_written, bytes_written


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate synthetic LogScope logs")
    parser.add_argument("--output", default="tests/fixtures/synthetic_100mb.log")
    parser.add_argument("--size-mb", type=int, default=100)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    if args.size_mb <= 0:
        raise SystemExit("--size-mb must be positive")

    output = Path(args.output)
    target_bytes = args.size_mb * 1024 * 1024
    lines, written = generate_log(output, target_bytes, args.seed)
    print(f"Created {output} | lines={lines} | bytes={written}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
