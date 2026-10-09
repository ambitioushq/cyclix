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

Anything found during the pass that none of these needs goes to "Parked" at the bottom of this file, and waits.

## Step 0: small fixes, in one PR

- [ ] `fail_under = 98` under `[tool.coverage.report]` in `pyproject.toml`.
- [ ] Branch protection on `main`: require conversation resolution and linear history. Decide whether admins are bound by the required checks.
- [ ] A ruleset that turns on Copilot code review for every PR.
- [ ] `.github/copilot-instructions.md`: a first version that points Copilot at `CLAUDE.md` and the design overview. Step 2 adds the tenets.
- [ ] Dependabot for GitHub Actions and the `uv` lock file.
- [ ] The OpenSSF Scorecard workflow, with its badge in the README.
- [ ] CodeQL for Python, on PRs and weekly.

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

### Weak tests

<!-- One line each: the rule that was broken, and the scenario that should have caught it. -->

### Design questions

<!-- One line each. Settled ones move to the design doc they belong in. -->

## Step 2: tenets, each with an enforcer

`docs/tenets.md` lists the rules the engine must keep. Each tenet has a statement, the reason for it, and the test or CI check that enforces it. A tenet only a reviewer can check is marked "by review", and `copilot-instructions.md` lists it.

- [ ] Write `docs/tenets.md`. Starting candidates, to confirm or change in step 1:
  - The loop never reads the event log to decide what to do next.
  - Only a tracker adapter names a tracker's own fields.
  - Stages reach the tracker, the code host, the agent and git only through the adapters.
  - Every action that changes the outside world is preceded by `set_phase`.
  - The runtime uses the standard library only.
  - The repository holds no private names, paths or tokens.
- [ ] Write the enforcers: small import and source tests in `tests/unit/test_tenets.py`.
- [ ] A test that fails when a tenet names no enforcer, or names one that does not exist.
- [ ] Add the "by review" tenets to `.github/copilot-instructions.md`.

## Step 3: test quality

Coverage shows which lines ran. A test can run a line and still pass when that line breaks, and mutation testing finds those tests.

- [ ] Mutation testing with `mutmut`, as a dev dependency. A workflow runs it by hand and weekly, never on a PR, like `sandbox.yml`.
- [ ] Record the first baseline here: planted faults that survived, for each part of the engine. Set a target for each.
- [ ] Close the gaps listed under "Weak tests" in step 1.
- [ ] Patch coverage on each PR, so new code cannot hide behind the overall number.
- [ ] A type checker (pyright or ty, to decide) as a dev dependency, run in CI.
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

## Parked

<!-- Found during the pass and outside "Done when". One line each. -->
