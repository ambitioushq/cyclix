# Contributing

This file explains how Cyclix is built and how you can help.

## How Cyclix is developed

One maintainer designs Cyclix and writes most of its code, working from one view of the whole engine. This is deliberate. One person holding the whole design keeps it consistent and keeps the bar for correctness high.

It does not mean the project is closed. The maintainer reads every issue and decides what becomes work. The contributions below are wanted.

## The most valuable ways to contribute

1. **Report bugs.** A bug you can reproduce is the most useful thing you can send. [Open an issue](https://github.com/ambitioushq/cyclix/issues/new/choose) with what you ran, what you expected, and what happened. Leave out secrets, tokens and private repository names, because issues are public. A security problem goes through private reporting instead, as [SECURITY.md](SECURITY.md) explains.
2. **Share use cases and design feedback.** Tell us where Cyclix fits your repository or workflow badly, or where the docs mislead you. [Open an issue](https://github.com/ambitioushq/cyclix/issues) for it.
3. **Fix the documentation.** Corrections and clarifications are welcome. [Open an issue](https://github.com/ambitioushq/cyclix/issues) for each one, naming the page and the fix.

## Code contributions

Only collaborators can open pull requests on this repository. Anyone can read the code, open issues and comment on pull requests.

To propose a code or documentation change, open an issue. Describe the problem, the change you have in mind, and why it fits Cyclix's design. The maintainer then makes the change. A contributor who has worked through several issues with the maintainer may be invited to become a collaborator.

AI tools can now write a pull request in minutes, but reviewing one still takes the maintainer hours. The review decides whether a change fits the design, and that judgement needs someone who understands the engine. Starting from an issue keeps review time for contributors who have that understanding.

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

Run the same checks CI runs before you push:

```sh
uv run ruff check
uv run ruff format --check
uv run complexipy
uv run coverage run -m pytest
uv run coverage report
(cd docs && npm ci && npm run build)
```

CI fails when test coverage drops below the floor set by `fail_under` in `pyproject.toml`, and when a function goes over a complexity limit. [ADR-0009](https://docs.cyclix.dev/adr/0009-fail-the-build-on-a-function-over-the-complexity-limits/) gives the limits and their reasons. The docs build fails when a link between pages reaches no page or heading.

[tests/README.md](tests/README.md) explains how the tests are laid out, and where a new scenario goes.
