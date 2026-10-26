# Project Instructions for aXet Code — LogScope

## Project context

You are implementing **LogScope**, a Python 3.11+ log-analysis CLI for operations teams. The source of truth for user-facing features, input assumptions, behavior, output contracts, and acceptance criteria is [`SPEC.md`](SPEC.md). Read it in full before taking action.

## Mandatory workflow — PLAN FIRST

**Do not implement or modify application source code until the user approves the plan.**

### Phase 1: Propose an implementation plan

1. Inspect the project folder and read `SPEC.md` and this file.
2. Present a concise but concrete implementation plan that covers:
   - Architecture and proposed file structure.
   - Shared streaming parser and malformed-line handling.
   - `summary`, `timeline`, and `grep` algorithms.
   - Plain-text, JSON, and Markdown formatting/output strategy.
   - How memory usage will remain suitable for a 100 MB log (including high-cardinality aggregation and streaming `grep` JSON).
   - CLI packaging/installability, error handling, and dependencies.
   - Test cases mapped to acceptance criteria A1–A12.
3. Identify ambiguous details or potential trade-offs. Recommend defaults consistent with `SPEC.md` rather than expanding scope.
4. End by requesting **approval of the plan**. Do not proceed to implementation yet.

### Phase 2: Implement only after approval

1. Set up an installable CLI exposing the `logscope` command.
2. Implement a reusable, well-tested streaming parser.
3. Implement the three commands with clean separation of parsing, aggregation, and output formatting.
4. Add tests as you go; include malformed input, empty input, out-of-order timestamps, 100 MB streaming, and output format tests.
5. Run the complete test suite and an end-to-end example of each command.
6. Produce a short completion summary: features implemented, tests passed/failed, exact commands to install and use the CLI, and any limitations.

## Coding standards

- Prefer the Python standard library (`argparse`, `datetime`, `json`, `pathlib`, `collections`, `sqlite3` where useful). Use `pytest` only as a test dependency if desired.
- Use type hints and small, focused functions. Avoid unnecessary abstractions.
- Never load the full log file into memory. Do not accumulate all `grep` matches in a list.
- Preserve output contracts in `SPEC.md`; keep JSON stdout free of warnings or logs.
- Count malformed lines and continue processing; surface errors cleanly on stderr.
- Use deterministic sort orders and test them.
- Do not silently overwrite existing Markdown reports.
- Keep generated sample files and large test logs out of version control (document or add them to `.gitignore`).
- Avoid network calls and external services; this is a local-only CLI.

## Definition of completion

Completion means passing the `SPEC.md` acceptance tests, demonstrating the memory-conscious 100 MB path, and documenting installation and usage in `README.md`. If any criterion cannot be met, report it clearly rather than claiming the project is complete.
