# Isolation: what the agent and the gate can reach

Cyclix runs a coding agent unattended, and then runs the code that agent wrote in the gate. This document is the design for keeping both away from the host's credentials and from the world outside the run. It was settled on 2026-10-09 in the Iteration 0.5 pass, as fix A in `docs/plans/iteration-0.5.md`. Part of it is built now and part of it later. "The order it is built in" at the end says which part lands in which PR.

## The problem

Everything the agent reads can carry instructions: the issue, the repository's files, review comments, web pages. Cyclix limits who can put work on the board, but a file already merged can still steer the agent. So the design assumes that an agent can be made to do anything its process is able to do. The question is what that process is able to do.

Today the answer is: everything the host user can do.

- The agent runs with the host's whole environment, because `adapters/claude_code.py` passes no `env=` to `subprocess.Popen`.
- It runs with `--permission-mode bypassPermissions`, so Claude Code allows every tool call without asking.
- It runs as the host user, so it can read every file in that user's home folder. On the self tenant's host, that includes the `gh` login in `~/.config/gh/hosts.yml` and the Claude login in `~/.claude/.credentials.json`.
- The gate runs the agent's code with the same environment and the same user (`stages/gate.py`).
- The loop opens its PRs under the maintainer's own GitHub identity, and admins may bypass branch protection on `main` (see "Cyclix as its own tenant" in `iteration-0.md`). An agent that reads the `gh` token can therefore merge a PR or push to `main` past the rules.

"Cyclix never merges" is kept today only because no agent has tried.

## What comparable agent runners do

Anthropic's cloud sessions of Claude Code, GitHub's Copilot coding agent and OpenAI's Codex cloud all follow the same five rules:

1. **The agent runs inside an isolation boundary**: a VM or container separate from the host. The boundary covers the whole agent process, including its file tools, hooks and MCP servers (Model Context Protocol servers, which give the agent extra tools), not only the shell commands it runs.
2. **No credential that can write to the repository enters the boundary.** Anthropic runs git through a proxy that sits outside the VM. Inside, git holds only a scoped credential. The proxy checks each push, allows it only to the session's own branch, and then adds the real GitHub token. Codex gives secrets only to a setup phase, and removes them before the agent starts. Copilot's agent can push only to branches whose names start with `copilot/`.
3. **Outgoing network traffic is blocked by default.** Each runner allows a short list of hosts, such as package indexes. Codex's agent phase has no internet at all unless the environment turns it on.
4. **Each task gets a fresh environment**, which is thrown away when the task ends.
5. **GitHub stays the final gate.** Branch protection and a required human review apply to everything the agent pushes.

Anthropic's own guidance for running Claude Code unattended says the same. An unattended session belongs in a container, a VM or Anthropic's sandbox runtime. Claude Code's built-in `/sandbox` setting is not enough on its own. It covers shell commands only, while the Read and Edit tools, hooks and MCP servers run outside it.

Sources:

- Claude Code, [Choose a sandbox environment](https://code.claude.com/docs/en/sandbox-environments) and [Sandboxing](https://code.claude.com/docs/en/sandboxing)
- Anthropic engineering, [Claude Code sandboxing](https://anthropic.com/engineering/claude-code-sandboxing)
- Claude Code, [Security](https://code.claude.com/docs/en/security)
- GitHub, [Customize the agent firewall](https://docs.github.com/en/copilot/how-tos/use-copilot-agents/coding-agent/customize-the-agent-firewall) and [Customize the agent environment](https://docs.github.com/en/copilot/how-tos/use-copilot-agents/coding-agent/customize-the-agent-environment)
- OpenAI, [Codex agent approvals and security](https://developers.openai.com/codex/agent-approvals-security) and [Codex cloud environments](https://developers.openai.com/codex/cloud/environments)

## The design

Cyclix follows the same five rules. The engine is the trusted part: it holds the GitHub credential and does every action that reaches GitHub. The agent and the gate are the untrusted part: they get the run's repository, a Claude login, and nothing else.

### 1. The agent and the gate run in a container

Each agent call and each gate run starts a fresh container with rootless Podman, and removes it when the call ends. Rootless means the container runs under the loop's own Unix user, with no daemon running as root. A process that escapes the container is still only that user.

- **What is mounted:** the run's repository, at `/work`, writable. Nothing else from the host. The host's home folder, `~/.config/gh`, `~/.ssh` and the SSH agent's socket (`SSH_AUTH_SOCK`) are absent from the container.
- **What the image holds:** Python, `uv`, git, and the `claude` command, at versions the tenant config pins. The tenant names the image in its config. Cyclix ships a starting image definition for Python repositories.
- **What the agent's home folder holds:** an empty home, made fresh for each container. Claude Code's first-start files (`~/.claude.json`) are written into it before the agent starts, so the CLI does not wait for a setup step. The agent does not load the maintainer's own `~/.claude` settings, plugins or `CLAUDE.md`, so a run behaves the same on any host.
- **Caches** that hold no secrets, such as `uv`'s package cache, live in a folder the engine keeps, so the gate does not download every package on every run. The setup step in point 5 mounts the cache writable. The agent and the gate get it read-only.

Why Podman: it runs without a root daemon, works under the systemd user manager that already runs the timer, and uses the standard container image format, so a tenant can build its image with any tool. Docker's daemon runs as root by default. A full VM per run (Firecracker, for example) gives a stronger boundary, but it costs much more to set up on one host. Anthropic's sandbox runtime (`@anthropic-ai/sandbox-runtime`) wraps a process without containers, but it is a beta research preview, its config format may change, and on Linux it builds its list of protected paths only once, at start.

Podman is a host requirement, like `git` and `gh`. It is not a Python dependency, so the rule "standard library only at runtime" still holds. `cyclix check` confirms that Podman is installed and can run a rootless container.

### 2. The only credential inside is the Claude login

The container gets one credential: the Claude login, through `CLAUDE_CODE_OAUTH_TOKEN` or `ANTHROPIC_API_KEY`. The engine reads it from its own environment and passes that one variable in. The agent can always read its own login; that is unavoidable, and the login allows spending on the Claude account but no change to the repository.

| Credential | Where it lives | Who can use it |
| --- | --- | --- |
| GitHub token (`gh` login) | The host user's `~/.config/gh`, or `GH_TOKEN` in the engine's environment | The engine only |
| Git push credentials | The engine's own repository and the `gh` login | The engine only |
| SSH keys and the SSH agent | The host | Nobody in the loop |
| Claude login | The engine's environment, passed into the container | The engine, the agent |

The gate gets no credential at all, the Claude login included.

### 3. A fresh clone for each run

Today each run is a git worktree of one clone per tenant. A worktree's `.git` is a file that points back into the main clone's `.git` folder, so mounting the worktree alone does not work, and mounting the main clone would hand the agent every other run's branches and the shared git config.

Each run instead gets its own clone, made by the engine from the engine's tenant clone with `git clone --no-hardlinks`. A hard-linked clone would share object files with the tenant clone, and an agent that rewrote one would corrupt the engine's own repository. The run's clone has no remote that can push: its `origin` is removed before the container starts. The run's branch is checked out in it, from the remote base or from the branch an earlier run left, as today.

### 4. The engine pushes from a repository the agent never touched

The agent can write anything inside the run's clone, including its `.git` folder. Git runs some of what it finds there: hooks in `.git/hooks`, and config keys such as `core.hooksPath`, `core.sshCommand`, `core.fsmonitor` and `credential.helper`. If the engine ran `git push` in the run's clone, it would run that code on the host, with the GitHub credential.

So the engine never runs git in a directory the agent could write. It does not fetch from the run's clone either: fetching from a local repository runs `git upload-pack` inside it, and git's own docs warn against doing that with a repository you do not trust. The handoff is a bundle, a single file that holds commits as plain data:

1. After the build, a fresh container (not the agent's) runs `git bundle create` for the run branch in the run's clone, and writes the file to a folder the engine reads.
2. The engine runs `git bundle verify` on the file, then fetches the branch from it into its own tenant clone, with `-c core.hooksPath=/dev/null` and `GIT_CONFIG_GLOBAL=/dev/null`. Fetching from a bundle file runs nothing from the run's clone.
3. The engine checks what arrived: the commit descends from the expected base, the branch name is the run's own, and no commit adds a git submodule.
4. The engine pushes that one branch to GitHub, without force, from the tenant clone.

The container in step 1 runs git in the run's clone, so any hook or config the agent planted runs there. That container holds no credential and has no network, so nothing it runs can reach further.

The engine reads the head SHA from the fetched commits, not from the run's clone.

### 5. Outgoing traffic is blocked unless the host is listed

- **The gate** runs with no network (`--network=none`). Its dependencies are installed first, in a separate setup step that runs the tenant's setup command (`uv sync --frozen` for a Python repository) with network access to the package index and no credentials. This copies Codex's two phases.
- **The agent** needs Anthropic's API. Its container has no direct route out. Its only route is a forward proxy that the engine runs on the host, which allows a listed set of hosts and refuses the rest: `api.anthropic.com`, plus `claude.ai` and `platform.claude.com` when the login is a subscription token, plus the package index. Claude Code honours `HTTPS_PROXY`, and so do `uv` and `pip`.

The exact way to give the container no route except the proxy (a Podman internal network with the proxy as its one member, or a network namespace the proxy shares) is settled when that part is built. See "Open questions".

### 6. A narrow GitHub identity for the engine

The engine's GitHub credential is narrowed, so that even a leaked token cannot change `main`:

- A separate identity for the loop: a GitHub App, as Release 2 already plans, or a fine-grained token on a machine user. It may write only to the tenant repository, with contents and pull-request rights and no admin rights.
- A ruleset that lets that identity push only to branches matching `cyclix/*`.
- Branch protection on `main` that requires one approving review. This becomes possible once the loop's PRs are no longer opened under the maintainer's own identity, because GitHub does not let an author approve their own PR.

`cyclix check` confirms that the base branch is protected (fix A2), and later that the loop's identity has no admin rights.

Most of this is GitHub settings that the maintainer changes, not code.

### 7. The agent may use only the tools its stage needs

Settled on 2026-10-09: the agent runs with `--permission-mode dontAsk --permission-prompts none` (Claude Code 2.1.259 or later), not with `bypassPermissions`. Each stage gets its own `--allowedTools` list, set in the tenant config. A tool call outside the list is refused, not allowed.

Settled on 2026-10-10: the engine also passes three more flags.

- `--restricted`. Claude Code then ignores the user, project and local settings files, so the repository's own `.claude/settings.json` cannot widen the tool list and its hooks do not run. The file tools are confined to the working directory, so the Read tool cannot reach `~/.config/gh`. Writes to settings and git files, such as `.git/hooks`, are refused. `bypassPermissions` is refused too.
- `--strict-mcp-config`, so the repository's MCP servers do not load.
- `--tools`, built from the stage's list: each rule adds its tool, so `Bash(git commit *)` adds `Bash`. The plan stage has no `Bash` rule, so it has no shell at all.

A test on 2026-10-10 with a subscription login confirmed this: a build-style call wrote and committed a file, and was refused `ls /` (allowed only by the repository's own settings file), a read of `/etc/hosts`, and a write to `.git/hooks/pre-push`. The agent still reads the repository's `CLAUDE.md`, which is not a settings file. It no longer loads the host user's own `~/.claude` settings, plugins or hooks.

**Where the settings live** (settled on 2026-10-10). Each stage has its own table in the tenant config, `[agent.plan]` and `[agent.build]`, holding `model`, `max_turns`, `max_budget_usd` and `tools`. The engine adds every flag in this point and in point 8 itself, and the config is refused if `agent.command` holds any of them, or a flag that widens what the agent may do (`--settings`, `--setting-sources`, `--mcp-config`, `--add-dir`, `--dangerously-skip-permissions`). So no config can turn these limits off.

- **Plan stage:** `Read`, `Grep`, `Glob`. Its prompt says "Do not change any files", and the list enforces it.
- **Build stage:** `Read`, `Grep`, `Glob`, `Edit`, `Write`; `Bash(git add *)`, `Bash(git commit *)`, `Bash(git status*)`, `Bash(git diff*)`, `Bash(git log*)`; and the tenant's own test commands, such as `Bash(uv run *)`. `git push` and `gh` are not on the list. The engine pushes and opens the PR itself.

**The build prompt lists the stage's tools** (settled on 2026-10-10). In a test, the agent joined `printf … > b.txt && git add … && git commit …` into one command. The whole command was refused, because `printf` is not on the list, and the agent gave up instead of retrying. The build prompt now lists the tools and commands the agent may use, and tells it to run each shell command on its own and to change files with the Write and Edit tools. With that prompt, the same test committed its change.

The list is not the boundary. `Bash(uv run *)` lets the agent run any Python it writes, and that Python can do anything the process can. The list is a cheaper second layer: it stops the agent from running a command such as `gh pr merge` because a file told it to, and it writes down what each stage is for. The cost is that a useful command missing from the list is refused, and that run fails until someone adds it.

`--bare` stays off. It skips the repository's own hooks and MCP servers, but it needs an API key, not a subscription login. Inside the container, those hooks and servers run within the boundary, so `--bare` is no longer needed for safety.

### 8. Every agent call has limits on time, turns and cost

Each agent call passes `--max-turns` and `--max-budget-usd`, set for each stage in the tenant config, on top of the existing timeout. The defaults, settled on 2026-10-09:

| Stage | `--max-turns` | `--max-budget-usd` |
| --- | --- | --- |
| Plan | 30 | 2 |
| Build | 100 | 5 |

The caps are there to stop a run that has gone wrong, not to squeeze a normal one. Each is about three times the largest of the self tenant's first five runs: plans took 6 to 10 turns and $0.37 to $0.76, and builds took 6 to 33 turns and $0.23 to $1.82. Five runs is a small sample, so the defaults are looked at again after about 20 more.

The budget cap also applies to a subscription login. There the amount is what the tokens would cost at API prices, not a charge, but tokens are what use up the subscription's usage limits, so the cap still limits how much of them one run can take. Claude Code checks the budget only when a turn ends, so a run can go past it by the cost of one turn.

The config is refused when `max_turns` is below 1 or `max_budget_usd` is not above 0, because such a cap stops nothing or stops everything. The same holds for the agent's `timeout_minutes`.

A run stopped by a cap ends with the subtype `error_max_turns` or `error_max_budget_usd`. The engine reports each as its own reason, "turn cap reached" or "budget cap reached", not as a general agent error. The event records the turn count beside the cost, so the caps can be checked against real runs.
 On a timeout, the engine sends SIGINT to the agent's process group, waits a short grace period, then sends SIGKILL. Claude Code ends its turn cleanly on SIGINT and still writes its result; SIGKILL leaves no result. The gate and every git call also get a timeout, and every git call sets `GIT_TERMINAL_PROMPT=0` so git never waits for a password.

## Logging in with a subscription token

The design works with a Claude subscription login as well as with an API key. The subscription login reaches the container as `CLAUDE_CODE_OAUTH_TOKEN`, made once with `claude setup-token`. Points to know:

- **A3 needs this token.** A login that Claude Code keeps in a file under `~/.claude` cannot be passed into the container, because the container gets no host files. The self tenant's host logs in that way today, so it moves to a token before A3 lands.
- **Make the token on a machine with a browser,** then put it in the environment file the timer loads. Tokens made over SSH inside a container have been reported as rejected.
- **The proxy must allow `claude.ai` and `platform.claude.com`** as well as `api.anthropic.com`. Claude Code's docs list them as needed for OAuth sign-in and token refresh. A run with an API key can leave them out.
- **Nothing else may compete with the token.** The container starts with an empty home, so no stale `~/.claude/.credentials.json` is there to override it, and `ANTHROPIC_API_KEY` must not be set beside it.
- **The token expires, and does not renew itself.** Anthropic does not document its lifetime; community reports say about a year. When it expires, every agent call fails. The engine reports a failed login as its own reason, distinct from an agent error, so the run does not look like a bad build.
- **Usage limits are shared.** The token draws on the same subscription as the maintainer's own use of Claude, so a busy day of interactive work can leave the loop at its limit, and the loop's runs can do the same to the maintainer.
- **`--bare` is unavailable,** because it needs an API key. Point 7 explains why the container makes that acceptable.
- **The terms are the subscription's terms.** `claude setup-token` exists for running Claude Code headless, such as in CI. A tenant runs Cyclix under its own login and its own plan.

## What this design does not stop

- **Sending out what the agent can read.** The agent can read the repository, and its traffic to Anthropic's API is allowed. Code it can read can leave through that route. A private repository's code is sent to the model provider in any case.
- **Bad code in a PR.** The agent can write harmful code on its own branch. The gate, the maintainer's review and branch protection are what stop it from reaching `main`.
- **Spending.** The agent holds the Claude login, so it can spend on that account up to the caps in point 8.
- **A kernel escape.** A container shares the host's kernel. A flaw in the kernel or in Podman could let a process out, as the loop's own user. A VM per run would close this, at a cost the single-host setup does not justify yet.

## The order it is built in

| Part | Contents |
| --- | --- |
| Fix A1 | The `dontAsk` mode, `--restricted`, `--strict-mcp-config` and per-stage tool lists (point 7). Turn and cost caps, and the turn count in the event (point 8). An environment allow-list for the agent and the gate (below). |
| Fix A2 | Timeouts on the gate and on git, `GIT_TERMINAL_PROMPT=0`, SIGINT before SIGKILL (point 8), and `cyclix check` confirming branch protection (point 6). |
| Fix A3 | The container for the agent and the gate (point 1), the Claude login as the only credential (point 2), a fresh clone per run (point 3), the push through a bundle (point 4), and the network rules (point 5). Several PRs. |
| Maintainer | The narrow GitHub identity, the ruleset and the required review (point 6). |

**The environment allow-list in A1.** Until A3, the agent runs on the host, so its environment is the one boundary A1 can tighten. The agent and the gate get:

- passed through from the engine: `PATH`, `HOME`, `USER`, `LOGNAME`, `LANG`, `LC_ALL`, `TERM` and `TMPDIR`, and, for the agent only, the Claude login (`CLAUDE_CODE_OAUTH_TOKEN`, `ANTHROPIC_API_KEY` and `CLAUDE_CONFIG_DIR`) when it is set. Claude Code looks its login up in the macOS Keychain by `USER`, and `CLAUDE_CONFIG_DIR` says where it keeps its login when that is not `~/.claude`. Without either, a test on 2026-10-10 got "Not logged in";
- set by the engine: `GH_CONFIG_DIR` pointing at an empty folder in the run folder, so `gh` finds no login; `GIT_CONFIG_GLOBAL=/dev/null` and `GIT_CONFIG_NOSYSTEM=1`, so git reads no credential helper from the user's or the system's config (git on macOS sets one in its system config); `GIT_TERMINAL_PROMPT=0`; and `GIT_AUTHOR_NAME`, `GIT_AUTHOR_EMAIL`, `GIT_COMMITTER_NAME` and `GIT_COMMITTER_EMAIL`, so commits still work without the user's config;
- the names the tenant lists in `pass_env`, under `[agent]` for the agent and under `[gate]` for the gate (settled on 2026-10-10). A tenant whose tests need, say, `DATABASE_URL` lists it there. It is usually empty. The config is refused if `pass_env` names a GitHub token, `GH_CONFIG_DIR`, `SSH_AUTH_SOCK`, a program git or SSH would ask for a credential (`GIT_ASKPASS`, `SSH_ASKPASS`, `GIT_SSH`, `GIT_SSH_COMMAND`), `GIT_TERMINAL_PROMPT`, or any `GIT_CONFIG*` variable, which can set a credential helper. The gate's `pass_env` also may not name the Claude login. So a typo in `pass_env` cannot undo this list;
- nothing else. `GH_TOKEN`, `GITHUB_TOKEN` and `SSH_AUTH_SOCK` are left out.

**The commits keep the engine's identity** (settled on 2026-10-10). The engine reads `user.name` and `user.email` from its own git config before hiding that config, and passes them in as the `GIT_AUTHOR_*` and `GIT_COMMITTER_*` variables. Each of the four takes the engine's own variable when it has one and the config otherwise, as git itself does, so setting `GIT_AUTHOR_NAME` alone changes the author and leaves the committer as configured. Commits are authored as they were before A1.

This removes every credential the agent could reach through its environment or through git's config. It does not stop Python that the agent runs through `Bash(uv run *)` from reading `~/.config/gh/hosts.yml` by its full path, because the agent still runs as the host user with the real `HOME`. (`--restricted` stops the Read tool from doing so.) For the same reason, the agent can still write files the engine later runs, such as hooks in the tenant clone. A3 closes both. Point 4 waits for A3, because until the agent is contained it adds nothing.

After A3, the allow-list stays as a second layer inside the container.

## Open questions

These are settled with the maintainer when the part that needs them is built.

1. Timeout values for the gate and for git calls (A2).
2. How the agent's container gets no route out except the proxy (A3).
3. Who builds and updates the container image, and how its versions are pinned (A3).
4. How a maintainer develops on macOS, where rootless Podman runs inside a VM (A3).
