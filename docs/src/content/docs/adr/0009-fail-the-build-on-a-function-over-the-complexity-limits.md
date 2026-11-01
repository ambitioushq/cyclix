---
title: "ADR-0009: Fail the build on a function over the complexity limits"
---

**Status:** Accepted

**Date:** November 2026

## Context

Cyclix's code is read far more often than it is written, and much of it is written in agent sessions. Without a limit, a function can keep gaining branches until no one can follow it. Before this decision, the check of each config value had a cyclomatic complexity of 20, and the check of the code host's branch protection reached 12 before it was split. Review catches some of this. A limit that fails the build catches it every time, and it costs no reviewer attention.

There are two common measures, and each misses what the other catches. Cyclomatic complexity counts the independent paths through a function: one, plus one for each branch or loop. A flat run of eleven `if` statements scores 11 and is easy to read. Cognitive complexity, defined by SonarSource, charges each branch and loop one more for every level it is nested in, and also charges for breaks in the flow. So it is closer to how hard the code is to read. A function with loops and conditions nested four deep can score 16 on cognitive complexity and only 8 on cyclomatic complexity.

## Decision

The build fails on a function over either limit. Both limits apply to the source, the tests and the scripts alike.

- **Cyclomatic limits, checked by ruff.** `C901` fails a cyclomatic complexity over 10. `PLR0911` fails more than 6 returns, `PLR0912` more than 12 branches, and `PLR0915` more than 50 statements. These are ruff's defaults. They are written out in `pyproject.toml`, so a reader sees them without knowing ruff's defaults. `PLR0913`, the argument count, stays off: a pytest-bdd step takes its fixtures as arguments, and argument count is not branch complexity.
- **A cognitive limit, checked by complexipy.** complexipy fails a cognitive complexity over 15, Sonar's default. It is a development tool, so [ADR-0004](/adr/0004-use-only-the-standard-library-unless-a-dependency-has-a-written-reason/) does not cover it.

CI runs both checks. The harness scenarios in `tests/harness/lint.feature` run both tools on the repository too, so `uv run pytest` alone fails on a complex function.

A function over a limit is split along what it does. A `noqa` for a complexity rule, or a raised limit, needs a reason in the PR that adds it.

## Consequences

- A function cannot grow past either limit without someone choosing to allow it, and the PR shows that choice.
- Splitting a function costs a few more names, and a reader may jump between them. A split along what the function does keeps each name worth reading.
- complexipy adds one development tool to install and one CI step.
- complexipy skips a file with no `.py` extension when it scans a folder, so `pyproject.toml` names each script in `tests/fakes/bin`. A new script there must be added to that list.

## Alternatives Considered

**A lower cyclomatic limit, such as 5 or 7.** This catches more, but it also fails flat functions that read easily, such as a list of guard clauses. It still misses deep nesting with few branches.

**Cognitive complexity alone.** This measures readability most closely, but it lets through a long flat function with many paths, each of which needs a test. Ruff's checks cost nothing extra, since ruff already runs.

**Review alone.** This costs no tooling. But a reviewer's attention runs out, and a limit no one checks drifts. The config value check reached 20 under review.
