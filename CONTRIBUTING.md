# Contributing

This file explains how Cyclix is built and how you can help.

## How Cyclix is developed

One maintainer designs Cyclix and writes most of its code, working from one view of the whole engine. This is deliberate. One person holding the whole design keeps it consistent and keeps the bar for correctness high.

It does not mean the project is closed. The maintainer reads every issue and decides what becomes work. The contributions below are wanted.

## The most valuable ways to contribute

1. **Report bugs.** A bug you can reproduce is the most useful thing you can send. [Open an issue](https://github.com/ambitioushq/cyclix/issues/new/choose) with what you ran, what you expected, and what happened. Leave out secrets, tokens and private repository names, because issues are public. A security problem goes through private reporting instead, as [SECURITY.md](SECURITY.md) explains.
2. **Share use cases and design feedback.** Tell us where Cyclix fits your repository or workflow badly, or where the docs mislead you. [Open an issue](https://github.com/ambitioushq/cyclix/issues) for it.
3. **Fix the documentation.** Corrections and clarifications are welcome. [Open an issue](https://github.com/ambitioushq/cyclix/issues) for each one. Once we agree on the fix, you can send it as a pull request.

## Code contributions

- **Every pull request starts with an issue**, even a typo or a one-line fix. Open the issue first, and write code once we agree on the approach there. A pull request that arrives without one is not merged, however good the code is. Most of a change's cost is not the diff. It is whether the change fits the design, and the work of keeping it up afterwards.
- **A pull request made with an AI tool meets the same bar, and the bar is understanding.** The pull request is tied to an agreed issue. You can explain every part of the change and why it fits Cyclix's design. A pull request that reads as unreviewed AI output is closed: one with no linked issue, generated boilerplate, or changes its author cannot explain. Judging whether a change fits the design is the real work, and a tool cannot do it for you.

None of this is a judgement of your work. It is how one maintainer keeps one design. If that does not suit you, the Apache license lets you fork Cyclix.

## Licensing

Cyclix is licensed under the [Apache License 2.0](LICENSE). When you send a contribution, it is licensed under the same terms, as section 5 of the license says. What comes in is licensed the same way as what goes out.

## Setting up locally

You need Python 3.14, [`uv`](https://docs.astral.sh/uv/), and Node 26 for the docs site. Clone the repository and install Cyclix with its development tools:

```sh
git clone https://github.com/ambitioushq/cyclix.git
cd cyclix
uv sync --locked
```

Run the same checks CI runs before you open a pull request:

```sh
uv run ruff check
uv run ruff format --check
uv run complexipy
uv run coverage run -m pytest
uv run coverage report
(cd docs && npm ci && npm run build)
```

CI fails when test coverage drops below the floor set by `fail_under` in `pyproject.toml`. The docs build fails when a link between pages reaches no page or heading.

[tests/README.md](tests/README.md) explains how the tests are laid out, and where a new scenario goes.
