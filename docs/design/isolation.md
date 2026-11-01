# Isolation: what the agent and the gate can reach

Cyclix runs a coding agent unattended, and then runs the code that agent wrote in the gate. Both must be kept away from the host's credentials and from the world outside the run. Part of that is built. Part is coming soon, and the last section lists which.

## The problem

Everything the agent reads can carry instructions: the issue, the repository's files, review comments, web pages. Cyclix limits who can put work on the board, but a file that is already merged can still carry instructions that the agent follows. So the design assumes that an agent can be made to do anything its process is able to do. The question is what that process is able to do.

Today the process is limited in three ways, and it is not contained:

- **The tools are limited.** Each stage has a list of tools, and the agent cannot use others.
- **The environment is limited.** The agent and the gate see an allow-list of environment variables, and git and `gh` find no credential in it.
- **The process is not contained.** The agent and the gate still run as the host user, with the real `HOME`. Code they run can read any file that user can read. Python started through `Bash(uv run *)` can read `~/.config/gh/hosts.yml` or `~/.netrc` by its full path. The agent's Read tool cannot, because `--restricted` confines it to the working directory. The agent can also write files that the engine later runs, such as hooks in the tenant's clone.

So the merge rule ([ADR-0001](../adr/0001-merge-only-after-approval-or-under-a-written-rule.md)) holds against an agent that follows its tool list. It does not yet hold against an agent that runs Python to read a token. Run Cyclix as a dedicated user that holds only the tokens the loop needs. If the operator's GitHub identity opens the PRs and may bypass branch protection, a leaked token can merge a PR or push to the base branch past the rules.

## What comparable agent runners do

Anthropic's cloud sessions of Claude Code, GitHub's Copilot coding agent and OpenAI's Codex cloud all follow the same five rules:

1. **The agent runs inside an isolation boundary**: a VM or container separate from the host. The boundary covers the whole agent process, including its file tools, hooks and MCP servers (Model Context Protocol servers, which give the agent extra tools), not only the shell commands it runs.
2. **No credential that can write to the repository enters the boundary.** Anthropic runs git through a proxy that sits outside the VM. Inside, git holds only a scoped credential. The proxy checks each push, allows it only to the session's own branch, and then adds the real GitHub token. Codex gives secrets only to a setup phase, and removes them before the agent starts. Copilot's agent can push only to branches whose names start with `copilot/`.
3. **Outgoing network traffic is blocked by default.** Each runner allows a short list of hosts, such as package indexes. Codex's agent phase has no internet at all unless the environment turns it on.
4. **Each task gets a fresh environment**, which is thrown away when the task ends.
5. **GitHub stays the final gate.** Branch protection and a required human review apply to everything the agent pushes.

Anthropic's guidance for running Claude Code unattended says the same. An unattended session belongs in a container, a VM or Anthropic's sandbox runtime. Claude Code's built-in `/sandbox` setting is not enough on its own. It covers shell commands only, while the Read and Edit tools, hooks and MCP servers run outside it.

Sources:

- Claude Code, [Choose a sandbox environment](https://code.claude.com/docs/en/sandbox-environments) and [Sandboxing](https://code.claude.com/docs/en/sandboxing)
- Anthropic engineering, [Claude Code sandboxing](https://anthropic.com/engineering/claude-code-sandboxing)
- Claude Code, [Security](https://code.claude.com/docs/en/security)
- GitHub, [Customize the agent firewall](https://docs.github.com/en/copilot/how-tos/use-copilot-agents/coding-agent/customize-the-agent-firewall) and [Customize the agent environment](https://docs.github.com/en/copilot/how-tos/use-copilot-agents/coding-agent/customize-the-agent-environment)
- OpenAI, [Codex agent approvals and security](https://developers.openai.com/codex/agent-approvals-security) and [Codex cloud environments](https://developers.openai.com/codex/cloud/environments)

## The design

Cyclix follows the same five rules ([ADR-0005](../adr/0005-confine-the-agent-and-the-gate.md)). The engine is the trusted part: it holds the GitHub credential and does every action that reaches GitHub. The agent and the gate are the untrusted part. They get the run's repository, a Claude login, and nothing else.

### What is built

- **The agent may use only the tools its stage needs.** The engine runs Claude Code with `--permission-mode dontAsk --permission-prompts none`, so a tool call outside the stage's list is refused, and adds `--restricted`, `--strict-mcp-config`, `--tools`, `--max-turns` and `--max-budget-usd`. The plan stage may use `Read`, `Grep` and `Glob`. The build stage may also use `Edit`, `Write`, some `git` commands and the tenant's test commands. The agent command in the config may hold only `-p`, `--print` and `--effort <level>`, and no config value that goes into a command or a path may start with `-`. The build prompt lists the stage's tools and asks for one shell command at a time, because a joined command is refused whole if any part of it is off the list. `--bare` stays off, because it needs an API key and not a subscription login. The `dontAsk` mode with `--permission-prompts none` needs Claude Code 2.1.259 or later. In a test with a subscription login, a build-style call wrote and committed a file. It was refused `ls /` (which only the repository's own settings file allowed), a read of `/etc/hosts`, and a write to `.git/hooks/pre-push`. The agent still reads the repository's `CLAUDE.md`, which is not a settings file. It no longer loads the host user's own `~/.claude` settings, plugins or hooks.
- **Every agent call has limits on time, turns and cost.** Each stage sets `max_turns` and `max_budget_usd`, and the agent has a timeout. See [Configuration](../reference/configuration.md#agentplan-and-agentbuild). The event records the turn count beside the cost, so the caps can be checked against real runs. In a small sample of runs, plans took 6 to 10 turns and $0.37 to $0.76, and builds took 6 to 33 turns and $0.23 to $1.82. The caps in the example config are about three times those figures.
- **The agent and the gate get an allow-list of environment variables, with no credential in it**. The lists are in [Configuration](../reference/configuration.md#what-the-agent-and-the-gate-see). Before it hides the user's git config, the engine runs `git var GIT_AUTHOR_IDENT` and `git var GIT_COMMITTER_IDENT` in the worktree and passes the names and emails in as `GIT_AUTHOR_*` and `GIT_COMMITTER_*`. `git var` resolves each role the way a commit would: the engine's own `GIT_*` variables first, then the repository's config, `author.*` and `committer.*`, `user.*`, and finally `EMAIL` and the system's defaults. So a tenant repository with its own `user.name` keeps it.
- **The gate and every git call have time limits**, and a call past its limit has its whole process group killed ([Configuration](../reference/configuration.md#time-limits-that-are-not-in-the-config)).
- **`cyclix check` confirms that the base branch is protected.** It fails unless the base branch requires a pull request and refuses force-pushes and deletion ([Commands](../reference/commands.md#the-checks-with-the-fix-for-each-failure)). It does not yet require an approving review, because the operator's GitHub identity opens the PRs, and GitHub does not let an author approve their own PR.

### 1. Coming soon: the agent and the gate run in a container

Each agent call and each gate run starts a fresh container with rootless Podman, and removes it when the call ends. Rootless means the container runs under the loop's own Unix user, with no daemon running as root. A process that escapes the container is still only that user.

- **What is mounted:** the run's repository, at `/work`, writable. Nothing else from the host. The host's home folder, `~/.config/gh`, `~/.ssh` and the SSH agent's socket (`SSH_AUTH_SOCK`) are absent from the container.
- **What the image holds:** Python, `uv`, git, and the `claude` command, at versions the tenant config pins. The tenant names the image in its config. Cyclix ships a starting image definition for Python repositories.
- **What the agent's home folder holds:** an empty home, made fresh for each container. Claude Code's first-start files (`~/.claude.json`) are written into it before the agent starts, so the CLI does not wait for a setup step. The agent does not load the host user's own `~/.claude` settings, plugins or `CLAUDE.md`, so a run behaves the same on any host.
- **Caches** that hold no secrets, such as `uv`'s package cache, live in a folder the engine keeps, so the gate does not download every package on every run. The setup step in point 5 mounts the cache writable. The agent and the gate get it read-only.

Why Podman: it runs without a root daemon, works under the systemd user manager that already runs the timer, and uses the standard container image format, so a tenant can build its image with any tool. Docker's daemon runs as root by default. A full VM for each run (Firecracker, for example) gives a stronger boundary, but it costs much more to set up on one host. Anthropic's sandbox runtime (`@anthropic-ai/sandbox-runtime`) wraps a process without containers, but it is a beta research preview, its config format may change, and on Linux it builds its list of protected paths only once, at start.

Podman is a host requirement, like `git` and `gh`. It is not a Python dependency, so the rule "standard library only at runtime" still holds ([ADR-0004](../adr/0004-use-only-the-standard-library-unless-a-dependency-has-a-written-reason.md)). `cyclix check` would confirm that Podman is installed and can run a rootless container.

### 2. Coming soon: the only credential inside is the Claude login

The container gets one credential: the Claude login, through `CLAUDE_CODE_OAUTH_TOKEN` or `ANTHROPIC_API_KEY`. The engine reads it from its own environment and passes that one variable in. The agent can always read its own login. That is unavoidable, and the login allows spending on the Claude account but no change to the repository.

| Credential | Where it lives | Who can use it |
| --- | --- | --- |
| GitHub token (`gh` login) | The host user's `~/.config/gh`, or `GH_TOKEN` in the engine's environment | The engine only |
| Git push credentials | The engine's own repository and the `gh` login | The engine only |
| SSH keys and the SSH agent | The host | Nobody in the loop |
| Claude login | The engine's environment, passed into the container | The engine, the agent |

The gate gets no credential at all, the Claude login included.

### 3. Coming soon: a fresh clone for each run

Today each run is a git worktree of one clone for each tenant. A worktree's `.git` is a file that points back into the main clone's `.git` folder, so mounting the worktree alone does not work, and mounting the main clone would hand the agent every other run's branches and the shared git config.

Each run would instead get its own clone, made by the engine from the engine's tenant clone with `git clone --no-hardlinks`. A hard-linked clone would share object files with the tenant clone, and an agent that rewrote one would corrupt the engine's own repository. The run's clone has no remote that can push: its `origin` is removed before the container starts. The run's branch is checked out in it, from the remote base or from the branch an earlier run left, as today.

### 4. Coming soon: the engine pushes from a repository the agent never touched

The agent can write anything inside the run's clone, including its `.git` folder. Git runs some of what it finds there: hooks in `.git/hooks`, and config keys such as `core.hooksPath`, `core.sshCommand`, `core.fsmonitor` and `credential.helper`. If the engine ran `git push` in the run's clone, it would run that code on the host, with the GitHub credential.

So the engine would never run git in a directory the agent could write. It would not fetch from the run's clone either: fetching from a local repository runs `git upload-pack` inside it, and git's own docs warn against doing that with a repository you do not trust. The handoff is a bundle, a single file that holds commits as plain data:

1. After the build, a fresh container (not the agent's) runs `git bundle create` for the run branch in the run's clone, and writes the file to a folder the engine reads.
2. The engine runs `git bundle verify` on the file, then fetches the branch from it into the tenant clone that the engine keeps, with `-c core.hooksPath=/dev/null` and `GIT_CONFIG_GLOBAL=/dev/null`. Fetching from a bundle file runs nothing from the run's clone.
3. The engine checks what arrived: the commit descends from the expected base, the branch name is the run's own, and no commit adds a git submodule.
4. The engine pushes that one branch to GitHub, without force, from the tenant clone.

The container in step 1 runs git in the run's clone, so any hook or config the agent planted runs there. That container holds no credential and has no network, so nothing it runs can reach further. The engine reads the head SHA from the fetched commits, not from the run's clone. Until the agent is contained, this adds nothing, so it waits for the container.

### 5. Coming soon: outgoing traffic is blocked unless the host is listed

- **The gate** runs with no network (`--network=none`). Its dependencies are installed first, in a separate setup step that runs the tenant's setup command (`uv sync --frozen` for a Python repository) with network access to the package index and no credentials. This copies Codex's two phases.
- **The agent** needs Anthropic's API. Its container has no direct route out. Its only route is a forward proxy that the engine runs on the host, which allows a listed set of hosts and refuses the rest: `api.anthropic.com`, plus `claude.ai` and `platform.claude.com` when the login is a subscription token, plus the package index. Claude Code honours `HTTPS_PROXY`, and so do `uv` and `pip`.

### 6. A narrow GitHub identity for the engine

This part is GitHub settings that the operator changes, not code. It narrows the engine's GitHub credential so that even a leaked token cannot change the base branch:

- A separate identity for the loop: a GitHub App, or a fine-grained token on a machine user. It may write only to the tenant repository, with contents and pull-request rights and no admin rights.
- A ruleset that lets that identity push only to branches matching `cyclix/*`.
- Branch protection on the base branch that requires one approving review. This becomes possible once the loop's PRs are not opened under the operator's own identity, because GitHub does not let an author approve their own PR.

Coming soon: `cyclix check` would also confirm that the loop's identity has no admin rights and that the review is required. The check that exists reads a rule whether it comes from classic branch protection or from a ruleset. Reading classic protection needs admin rights, which the narrow identity will not have, so a ruleset that holds every rule is enough on its own. When neither source can be read, the check fails and says so, because it cannot confirm the branch is protected.

## Logging in with a subscription token

The design works with a Claude subscription login as well as with an API key. The subscription login reaches the agent as `CLAUDE_CODE_OAUTH_TOKEN`, made once with `claude setup-token`. Things to know:

- **Make the token on a machine with a browser,** then put it in the environment file the timer loads. Tokens made over SSH inside a container have been reported as rejected.
- **Nothing else may compete with the token.** `ANTHROPIC_API_KEY` must not be set beside it. With the container, the empty home means no stale `~/.claude/.credentials.json` can override it.
- **The token expires, and does not renew itself.** Anthropic does not document its lifetime. Community reports say about a year. When it expires, every agent call fails.
- **Usage limits are shared.** The token draws on the same subscription as the operator's own use of Claude, so a busy day of interactive work can leave the loop at its limit, and the loop's runs can do the same to the operator.
- **`--bare` is unavailable,** because it needs an API key. The container is what would make that acceptable.
- **The terms are the subscription's terms.** `claude setup-token` exists for running Claude Code headless, such as in CI. A tenant runs Cyclix under its own login and its own plan.

Coming soon, with the container:

- A login that Claude Code keeps in a file under `~/.claude` cannot be passed into the container, because the container gets no host files. A host that logs in that way has to move to a token.
- The proxy must allow `claude.ai` and `platform.claude.com` as well as `api.anthropic.com`. Claude Code's docs list them as needed for OAuth sign-in and token refresh. A run with an API key can leave them out.
- The engine would report a failed login as its own reason, distinct from an agent error, so the run does not look like a bad build.

## What this design does not stop

- **Sending out what the agent can read.** The agent can read the repository, and its traffic to Anthropic's API is allowed. Code it can read can leave through that route. A private repository's code is sent to the model provider in any case.
- **Bad code in a PR.** The agent can write harmful code on its own branch. The gate, a person's review and branch protection are what stop it from reaching the base branch.
- **Spending.** The agent holds the Claude login, so it can spend on that account up to the caps.
- **A kernel escape.** A container shares the host's kernel. A flaw in the kernel or in Podman could let a process out, as the loop's own user. A VM for each run would close this, at a cost the single-host setup does not justify.

## What is built and what is coming soon

| Part | State |
| --- | --- |
| Tool lists, `dontAsk` mode, `--restricted` and `--strict-mcp-config` | Built |
| Turn, cost and time caps, and the turn count in the event | Built |
| Environment allow-list for the agent and the gate | Built |
| Time limits on the gate and on git, SIGINT before SIGKILL, and stream-json output | Built |
| `cyclix check` confirms that the base branch is protected | Built |
| The container for the agent and the gate (point 1) | Coming soon |
| The Claude login as the only credential inside (point 2) | Coming soon |
| A fresh clone for each run (point 3) | Coming soon |
| The push through a bundle (point 4) | Coming soon |
| The network rules and the proxy (point 5) | Coming soon |
| The narrow GitHub identity, the ruleset and the required review (point 6) | The operator's GitHub settings. The check for them is coming soon. |

## Still to design

These belong to the container and are decided when it is built:

1. How the agent's container gets no route out except the proxy: a Podman internal network with the proxy as its one member, or a network namespace the proxy shares.
2. Who builds and updates the container image, and how its versions are pinned.
3. How a developer works on macOS, where rootless Podman runs inside a VM.
