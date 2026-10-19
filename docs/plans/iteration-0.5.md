# Iteration 0.5: foundations

Iteration 0 got a real issue through the loop to a merged PR. Before the first area opens, this pass makes the repository a sound base to build on. It covers four things: the maintainer understands every part of the code, the rules the code must keep are written down and checked, the docs stay true to the code, and the loop's shape can be changed without losing track of it.

The work is done by hand, in supervised sessions, from this file. Most of it is judgement and design, so it stays in one plan and is kept off the loop's issue queue. One umbrella issue holds the pass on the board. Each PR says `Refs #55` in place of `Closes`, and names the section of this file it covers. Tick a box in the same PR that does the work.

No new features are built until the pass is done. The loop keeps running on its own tenant meanwhile.

## Done when

- [ ] Every tenet in `docs/tenets.md` names a test or CI check that enforces it, or is marked "by review".
- [ ] A mutation testing baseline is recorded, with a target for each part of the engine.
- [ ] The reference docs are generated from the code, and CI fails when they differ.
- [ ] The loop table drives the runner, and the loop diagram is generated from it.
- [ ] Copilot reviews every PR against the repository's own instructions.
- [ ] The PRs in "Fixes from the findings, in PR order" are merged.

Anything found during the pass that none of these needs goes to "Parked" at the bottom of this file, and waits.

## Step 0: small fixes, in one PR

- [x] `fail_under = 98` under `[tool.coverage.report]` in `pyproject.toml`.
- [x] Branch protection on `main`: require conversation resolution and linear history. Admins are not bound by the required checks. Each new check (zizmor, `uv audit`, gitleaks, CodeQL) becomes required after a few clean runs.
- [x] A ruleset that turns on Copilot code review for every PR.
- [x] `.github/copilot-instructions.md`: a first version that points Copilot at `CLAUDE.md` and the design overview. Step 2 adds the tenets.
- [x] Dependabot for GitHub Actions and the `uv` lock file.
- [x] The OpenSSF Scorecard workflow, with its badge in the README.
- [x] CodeQL for Python, on PRs and weekly.
- [x] zizmor, which checks workflow files for security mistakes, run in CI.
- [x] Workflow permissions: `permissions: {}` at the top of each workflow, granted per job, and `persist-credentials: false` on every checkout.
- [x] harden-runner, version 2.16 or later, on each job, first in audit mode.
- [x] The sandbox secrets move to a protected GitHub environment.
- [x] `uv audit` in CI. It is a preview feature, so it runs with `--preview-features audit`.
- [x] gitleaks in CI, and GitHub push protection turned on.
- [x] `CODEOWNERS` and issue templates.

## Step 1: understand the code, by tracing a real run

Seven sessions, one per layer, in the order the code runs. Each session does three things:

1. **Trace.** Start from one real run on the self tenant (the run that took #35 to PR 36 is a good first one): its event lines, its rows in SQLite and its run folder. Then read the code that produced them.
2. **Break one rule.** Change it on a scratch branch, predict which scenarios should fail, and run the suite. When nothing fails, record the gap under "Weak tests" below. Throw the branch away.
3. **Sort every question** into one of three places: a line in `docs/architecture.md`, a finding below, or a design question for the maintainer.

- [ ] 1. Work states and the transition table (`workstate.py`)
- [ ] 2. The state core (`state/`)
- [ ] 3. The adapters: tracker, code host, agent (`adapters/`)
- [ ] 4. The sweep and the runner (`runner.py`)
- [ ] 5. The stages and their prompts (`stages/`)
- [ ] 6. The event log (`events/`)
- [ ] 7. Config, install, the CLI, and the test fakes (`config.py`, `install.py`, `cli.py`, `tests/fakes/`)
- [ ] `docs/architecture.md` written: the parts, one issue's path through them, and who owns each fact, with a diagram.

### Findings

<!-- One line each: what, where (file:line), and what to do. -->

Line numbers in both reads below are against `main` at 46f508a. Check each one against the current code before acting on it.

Found in the first read of the whole repository, before the tracing sessions:

Structure and guardrails:

- Only 30 of about 160 functions declare a return type, and many parameters have no type, such as `Agent.run` in `adapters/agent.py:24`. Type every public function, and add pyright in strict mode (step 3).
- The package has no `py.typed` marker, so type checkers treat it as untyped. Add `src/cyclix/py.typed`.
- The engine reports through `print` and writes no logs, as in `runner.py:57` and `runner.py:160`. Use the `logging` module, writing to stderr so journald keeps it, kept apart from the event log.
- The seven error classes (`ConfigError`, `InstallError`, `StateError`, `GhError`, `TrackerError`, `CodeHostError`, `EventError`) share no base class, so `runner.py:50` lists six of them by hand. Add one `CyclixError` base.
- Ruff selects only the `I`, `UP` and `B` rule sets (`pyproject.toml`). Widen the set and record why each set is on or off.
- Stages come in two shapes. Admission and the reconciler are module functions with their own signatures (`stages/admission.py:16`, `stages/reconciler.py:25`). The other stages are classes on the `Stage` protocol. Give them one shape before `decide()` picks between them.
- Two modules outside `adapters/` import `subprocess`: the gate stage (`stages/gate.py:8`) and `install.py`. The tenet "only adapters import `subprocess`" fails on both, as an import-linter trial run showed. Move each behind an adapter, or name it in the tenet as an exception.
- Stages import the GitHub adapter directly: `slug` and `branch_name` from `adapters/github_codehost.py`, in `stages/admission.py:8` and `stages/reconciler.py:7`. Branch naming belongs behind the `CodeHost` protocol.
- The same list of work states is kept twice: `config.STATES` (`config.py:16`) and `workstate.State` (`workstate.py:10`). Derive one from the other.
- `Writer.ANY_STATION` (`workstate.py:31`) still uses the old word "station". Rename it.
- `cyclix check` reads the board with `gh project field-list` (`cli.py:142`). That is the costly call the tracker stopped making in #47. Reuse `GitHubTracker.board()`.
- The CLI keeps every subcommand in one module (`cli.py`). One module per subcommand, each with `run(args) -> int`, scales better as commands are added.
- `config.version` hashes the file's raw bytes (`config.py:140`), so a whitespace edit is a new version. Hash a normalised form instead.

Safety:

- The gate runs commands with no timeout (`stages/gate.py:41`). A hung test suite keeps the pass running while it holds the lock. Every later pass then prints "another pass is running" and exits 0, and nothing alerts. Add a timeout like the agent's.
- Every open run counts as crashed, because a claim has no expiry (`runner.py:107`). This is safe today only because of the lock. A claim with an expiry that progress renews (a lease) replaces it.
- The example config runs the agent with `--permission-mode bypassPermissions` and without `--bare` (`docs/examples/tenant.toml`). The tenant repository's own hooks and MCP servers then run inside the unattended session. Record this as a decision. `--bare` needs an API key, not a subscription login.

Behaviour, found while reading:

- The reconciler finds an item's PR by a branch name built from the issue's current title (`stages/reconciler.py:19`). If the title is edited after the PR opens, the PR is never found, and the item stays In review with no alert. A new run on a retitled issue also starts a fresh branch (`adapters/github_codehost.py:63`). No scenario covers this.
- Some event fields are never filled: `cyclix.trust_level` is always null (`events/schema.py:22`), and `cyclix.round` is always 1 (`state/core.py:34`). Spend is recorded (`stages/base.py:72`) and no limit reads it.
- The work states stop at six (`workstate.py:10`). A Status with no Cyclix state and an item missing from the board both read as `None` (`adapters/github_tracker.py:89`), so the two cannot be told apart.

Found in a second review, against `main` at 46f508a:

Safety:

- The agent inherits the host's whole environment (`adapters/claude_code.py:53` passes no `env=`), and runs with `bypassPermissions`. It holds the host's `gh` login, so it can run `gh pr merge` or push to `main`. "Cyclix never merges" is kept today only by what the token may do. Pass the agent an allow-list of environment variables with no GitHub credentials; the engine already pushes for it.
- The gate runs code the agent wrote, with the same whole environment (`stages/gate.py:41`). Give it the same allow-list.
- git calls have no timeout, and nothing stops git asking for a password (`adapters/github_codehost.py:33`). A push whose credentials fail waits forever while it holds the lock. Set `GIT_TERMINAL_PROMPT=0` and a timeout, as `adapters/gh.py` does.
- `cyclix check` does not confirm that the base branch is protected. Branch protection is the final gate in `SECURITY.md`, so check for it.
- The systemd service has no start timeout (`install.py:113`), and a oneshot service waits forever by default. It also has no sandboxing. Add `TimeoutStartSec`, `NoNewPrivileges=yes`, `ProtectSystem=strict` with `ReadWritePaths` for the state folder, `PrivateTmp=yes` and `UMask=0077`.
- The event log is created readable by every user (`events/log.py:65`, mode 0o644), and the state folder, `state.db` and the run folders use the default umask. Run folders hold prompts, issue text and agent answers. Use 0o700 for folders and 0o600 for files.
- An event can be lost, which the design says cannot happen. `runner.py:224-226` closes the run row in SQLite, then appends the event. A crash between the two leaves a closed row and no event, and the next sweep never sees it. Record on the row whether its event was written, and have each sweep write the missing ones (the outbox pattern).
- Run ids have one-second precision (`runner.py:241`), so two runs on one issue in the same second collide on the `runs` unique key. Python 3.14's `uuid.uuid7()` is unique and ordered by time.

Found in the research on comparable loops and on Claude Code's print mode:

- The agent timeout kills Claude Code's process group with SIGKILL (`adapters/claude_code.py:67`). Claude Code's docs say a SIGINT ends the session's turn cleanly, while SIGTERM gives exit 143 and no result. Send SIGINT first, wait a short grace period, then SIGKILL.
- Agent calls run with no `--max-turns` or `--max-budget-usd` cap (`docs/examples/tenant.toml`). The timeout bounds time only. Comparable loops cap turns and cost on every agent call. Set both per stage in the config.
- The `bypassPermissions` decision has a named alternative: `--permission-mode dontAsk` with `--permission-prompts none` (Claude Code 2.1.259 or later), plus `--allowedTools` limited by prefix rules such as `Bash(git commit *)`. Anything outside the list is then refused instead of allowed.

Structure:

- The wiring always builds the GitHub adapters (`runner.py:59-63`), whatever `kind` the config names. A small factory keyed by `kind` is where a second tracker plugs in.
- `GitHubTracker` lets `gh.GhError` out (`adapters/github_tracker.py:113`, `:120`, `:134`), so the runner catches a GitHub error by name (`runner.py:50`). Each adapter turns vendor errors into its protocol's error.
- Fixed sets of values are plain strings: outcomes (`stages/base.py:23`, `events/schema.py:61`), PR states (`adapters/codehost.py:28`), phases, and stage names, which are listed three times (`events/schema.py:60`, `workstate.Writer`, `runner.STAGES`). Make each one `StrEnum`, defined once.
- Untyped dicts cross module boundaries: board items (`adapters/github_tracker.py:205`), `board()` (`:144`), and event fields as `dict[str, object]`. Use dataclasses. The event can be one frozen dataclass with a method that writes its JSON form.
- Frozen dataclasses hold plain dicts, so they can still change: `Limits.wip` (`config.py:78`) and `StageResult.fields` (`stages/base.py:51`). Add `slots=True` and `kw_only=True`, and hold read-only mappings or tuples.
- The config schema is written twice: as dataclasses, and as the hand-written checker in `config.py:168-220`. Build the check from the dataclass fields and their types, so a new key is one line.
- Tests replace module globals at run time because the code takes no parameter for them: `runner.STAGES`, `gh.TIMEOUT`, `claude_code.SECONDS_PER_MINUTE`, `sqlite.MIGRATIONS`. Pass stages, timeouts and the clock in. The state core takes a clock, but `runner.py:241` and `events/log.py:39` call `datetime.now` themselves. The closure dict in `runner.py:173-180` comes from the same gap.
- Migrations are split on `;` (`state/sqlite.py:122`), which breaks on a trigger or a string holding a semicolon. Keep each migration as a list of statements, and make the tables `STRICT`, so SQLite checks column types.
- Pyright already reports 6 errors on code with almost no types: Protocol methods with no body (`adapters/tracker.py:37-49`), `round()` on `object | None` (`events/log.py:36`), and a dict type mismatch (`stages/reconciler.py:38`).
- Two "state" ideas sit side by side: `workstate.py` and the `state/` package. Rename `state/` to `store/`, since it is the SQLite store.
- `adapters/` mixes the protocols with the GitHub code. Move the GitHub code to `adapters/github/` (`gh.py`, `tracker.py`, `codehost.py`), so a Jira adapter gets a folder of its own.
- The stage class `stages/pr.PR` has the same name as the `codehost.PR` dataclass. Rename the stage class.
- The version is written twice, in `src/cyclix/__init__.py` and `pyproject.toml`. Read it with `importlib.metadata.version("cyclix")`.

### Weak tests

<!-- One line each: the rule that was broken, and the scenario that should have caught it. -->

### Design questions

<!-- One line each. Settled ones move to the design doc they belong in. -->

- Step 5 predates the loop-model design settled on 2026-10-08. That design chose one fixed workflow with steps a tenant can switch off, which settles the first box of step 5. It also replaces the stage table with decision tables read by a pure `decide()`, and adds two privacy steps: a data class on every event field, and one function every person's id passes through. Rewrite step 5 to match, in its own PR.
- Step 2's candidate tenets should also include the loop model's eight: decisions are a pure function of what was observed, the model version and the config version; every value has a fixed, finite list of values; every result that can vary is recorded once, as typed data; CI proves the model complete and free of overlaps; actions declare their effects, and every miss is recorded; the model is data, versioned by a content hash, and every view of it is generated; every override is part of the model and measured; every field has a data class, and every store is limited to one tenant.
- The event log is a custom JSON shape with a random trace id for each event (`events/log.py:37`). The loop-model design chose OpenTelemetry's JSON encoding (OTLP). Settle when schema 0 moves to it.
- Decision tables: use the "Unique" hit policy from DMN, the decision-table standard, where no two rules may match the same case, plus one catch-all rule per table that routes to a person. "First" and "Priority" make overlaps legal, and the overlap check would then find nothing.
- OpenTelemetry's `gen_ai.*` names moved to their own repository in June 2026, with no tagged release yet, and `gen_ai.provider.name` is now required. Pin a commit of that repository, and keep fields for cost under `cyclix.*`.
- The step 4 generator for `docs/reference/` and the generated views of the loop model should be one generator.
- Step 5's coverage and overlap checks can step through every combination of values, one table at a time. Every state variable has a short, fixed list of values, and each column's table tests only a few of them. The interval algorithms in the DMN research (Calvanese and others, 2016) are built for numeric ranges, which the loop model does not have.

## Step 2: tenets, each with an enforcer

`docs/tenets.md` lists the rules the engine must keep. Each tenet has a statement, the reason for it, and the test or CI check that enforces it. A tenet only a reviewer can check is marked "by review", and `copilot-instructions.md` lists it.

- [ ] Write `docs/tenets.md`. Starting candidates, to confirm or change in step 1:
  - The loop never reads the event log to decide what to do next.
  - Only a tracker adapter names a tracker's own fields.
  - Stages reach the tracker, the code host, the agent and git only through the adapters.
  - Every action that changes the outside world is preceded by `set_phase`.
  - The runtime uses the standard library only.
  - The repository holds no private names, paths or tokens.
- [ ] Write the enforcers: import-linter contracts for the import rules, and small source tests in `tests/unit/test_tenets.py` for the rest.
- [ ] A test that fails when a tenet names no enforcer, or names one that does not exist.
- [ ] Add the "by review" tenets to `.github/copilot-instructions.md`.

## Step 3: test quality

Coverage shows which lines ran. A test can run a line and still pass when that line breaks, and mutation testing finds those tests.

- [ ] Mutation testing with `mutmut`, as a dev dependency. A workflow runs it by hand and weekly, never on a PR, like `sandbox.yml`.
- [ ] Record the first baseline here: planted faults that survived, for each part of the engine. Set a target for each.
- [ ] Close the gaps listed under "Weak tests" in step 1.
- [ ] Patch coverage on each PR, so new code cannot hide behind the overall number.
- [ ] pyright in strict mode as a dev dependency, run in CI.
- [ ] Hypothesis stateful tests for the transition table and the state core. They run random sequences of moves and check the rules after each one.
- [ ] A rule in `tests/README.md`: a scenario's Then steps check an effect outside the engine (the board, the gh calls, git, the event log), never its internal state. Add it to `copilot-instructions.md`.

## Step 4: docs that cannot drift

The layout follows the Diátaxis split that most open-source projects use:

```
docs/
  architecture.md     the map (step 1)
  tenets.md           the rules and their enforcers (step 2)
  concepts/           what each idea is and why: work states, stages, the event log, trust
  reference/          generated from the code: states and transitions, event schema, config keys, CLI, the loop
  design/             why each part is built the way it is, one file per area
  plans/              plans like this one
```

- [ ] A script, `scripts/gen_reference.py`, that writes `docs/reference/` from the code. CI runs it and fails if the output differs from what is committed, the same way the gh shapes are checked.
- [ ] Concept pages for work states, stages and the event log.
- [ ] Split `docs/design/iteration-0.md`: reference material moves to `reference/`, explanation to `concepts/`, and the design calls stay.
- [ ] Docstrings link to their concept section. A test fails when a link from the code to the docs does not resolve.

## Step 5: the loop as one declared table

Today the stage order is the `STAGES` tuple in `runner.py`, the transitions are in `workstate.py`, and each stage's prompt, model and caps are spread across its module. The aim is one table that lists the stages in order and, for each one, its outcomes, the state each outcome moves the item to, its prompt file, its model, its phase points and its caps.

- [ ] Settle first: one opinionated workflow with steps that can be switched on and off, or support for many workflows. The current lean is one opinionated workflow. The table would stay internal, and the tenant config would not expose it.
- [ ] Write the table, and have the runner read it.
- [ ] Generate `docs/reference/loop.md` from it, with a diagram.
- [ ] A test that every stage and outcome pair in the table has a scenario tagged with it.
- [ ] A contract for each stage: what it reads and writes at each boundary (the tracker, the code host, the agent, git, the event log). These are the boundaries the Gherkin scenarios already use.

## Fixes from the findings, in PR order

The findings above go out as these PRs. The safety PRs come first and do not wait for step 1, because the loop already runs on its own tenant with these gaps. Each later PR goes in after step 1's session for the layer it changes, so each session traces the code before it changes.

The loop-model rewrite in step 5 will reshape the runner and the stages. These PRs fix what that rewrite keeps: types, errors, adapter boundaries, wiring and the store. The runner's shape and the two stage shapes wait for step 5.

- [ ] A. Subprocess boundaries, to the design in `docs/design/isolation.md`. Tick this box when A3 lands.
  - A1. `--permission-mode dontAsk` with a list of allowed tools for each stage, turn and cost caps on every agent call, and an environment allow-list for the agent and the gate, with no GitHub credentials.
  - A2. The gate timeout, a timeout and `GIT_TERMINAL_PROMPT=0` for git, SIGINT before SIGKILL on the agent timeout, and `cyclix check` confirming branch protection.
  - A3. The agent and the gate in a rootless Podman container, with the Claude login as the only credential, a fresh clone for each run, the push through a git bundle, and outgoing traffic only to listed hosts. Several PRs.
  - The maintainer moves the loop to its own GitHub identity, limits it to `cyclix/*` branches, and requires an approving review on `main`.
- [ ] B. Install and files: the systemd start timeout and sandboxing, and file modes for the state folder, `state.db`, the event log and run folders.
- [ ] C. The event outbox, `uuid7` run ids, and claims that expire unless progress renews them (a lease), with a scenario for a crash between closing the row and writing the event.
- [ ] D. Names and layout: `state/` to `store/`, `adapters/github/`, the PR stage class, `Writer.ANY_STATION`, the version from package metadata. These moves come before typing, so the typing PRs touch the final paths.
- [ ] E. Types: every public function typed, `py.typed`, the 6 pyright errors fixed, and pyright strict in CI. One PR per layer if it grows too large to review.
- [ ] F. Fixed values and typed data: one `StrEnum` each for outcomes, PR states, phases and stage names; the work states defined once; dataclasses with `slots` and `kw_only` holding read-only data; typed board items and a typed event.
- [ ] G. Errors and adapter boundaries: the `CyclixError` base, each adapter turning vendor errors into its own, branch naming behind `CodeHost`, and `cyclix check` reading the board through the tracker. The branch name is stored when the run starts, so a retitled issue still finds its PR. A Status with no Cyclix state reads differently from an item missing from the board.
- [ ] H. Wiring: the adapter factory keyed by `kind`; stages, timeouts and the clock passed in, with no module globals replaced in tests; `logging` in place of `print`; one module per CLI subcommand.
- [ ] I. Config: the check built from the dataclasses, and a config version that ignores whitespace.
- [ ] J. Store: migrations as lists of statements, and `STRICT` tables, through a migration from schema 1 to 2.
- [ ] K. Lint and import rules: ruff `ALL` with each ignored rule written down with its reason, and import-linter in CI with the contracts from step 2.

## Parked

<!-- Found during the pass and outside "Done when". One line each. -->

- Supply-chain and release guardrails beyond step 0: PyPI trusted publishing with build attestations, and the OpenSSF Best Practices badge.
- A per-issue failure count with a "not before" time in the state core, so an issue that keeps failing waits longer between attempts instead of retrying on every pass.
- Log the GraphQL rate limit (`rateLimit { cost remaining resetAt }`) on every pass.
- Record the head SHA each derived fact was computed for, such as a gate result, so a fact about an old commit shows as out of date. Kubernetes records `observedGeneration` for the same reason.
- `claude -p --resume` reports cost for the whole conversation, earlier runs included. A resumed session's cost must subtract the previous total.
- Record how many tool calls `dontAsk` refused in each agent call. Claude Code lists them under `permission_denials` in its JSON result. A stage whose tool list is too narrow then shows up in the event log, not only as a failed run.
- A hard cap on CI fix rounds: Stripe's coding agents stop after two CI rounds and hand the branch to a person.
