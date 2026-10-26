from __future__ import annotations

import argparse
import subprocess
import sys
import time
import tracemalloc
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _run(args: list[str]) -> tuple[float, int]:
    tracemalloc.start()
    start = time.perf_counter()
    completed = subprocess.run(
        [sys.executable, "-m", "logscope.cli", *args],
        cwd=ROOT,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=True,
        text=True,
    )
    _ = completed.returncode
    elapsed = time.perf_counter() - start
    _, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    return elapsed, peak


def main() -> int:
    parser = argparse.ArgumentParser(description="Benchmark LogScope runtime and memory")
    parser.add_argument("--log-file", default="tests/fixtures/synthetic_100mb.log")
    args = parser.parse_args()

    log_file = Path(args.log_file)
    if not log_file.is_absolute():
        log_file = ROOT / log_file

    if not log_file.exists():
        raise SystemExit(f"Log file not found: {log_file}")

    scenarios = [
        ["summary", str(log_file)],
        ["timeline", str(log_file), "--bucket", "15m"],
        ["grep", str(log_file), "--level", "ERROR", "--format", "json"],
    ]

    print(f"Benchmark file: {log_file}")
    print("command,runtime_seconds,peak_bytes")
    for command in scenarios:
        elapsed, peak_bytes = _run(command)
        print(f"{' '.join(command)},{elapsed:.3f},{peak_bytes}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
