# Cyclix

Cyclix runs an unattended issue-to-PR loop. It takes a well-formed issue from a board, plans the change, builds it, runs the quality gate, reviews it adversarially, opens a pull request, and carries that PR to a human merge. A person reviews and merges every PR.

**Pre-release. Not ready for use.** The code is written in public from the first commit. Interfaces will change without notice until v0.1.

## Usage

Each command takes the name of a tenant. The tenant's config is read from the path in `CYCLIX_CONFIG`, else `~/.config/cyclix/<tenant>.toml` (`$XDG_CONFIG_HOME` is used if set). The examples use a tenant named `cyclix`.

Check that the config loads, `gh` is signed in, the state directory is writable, the agent is on `PATH` and the board has every Status option:

```sh
cyclix check --tenant cyclix
```

Make one pass of the loop (`--once` is required):

```sh
cyclix run --once --tenant cyclix
```

Run the loop on a systemd user timer, every 10 minutes by default. `--every` sets another span, `--dry-run` prints the units and changes nothing, and `--force` replaces units that differ:

```sh
cyclix install --tenant cyclix
```

Stop the timer and remove its units:

```sh
cyclix uninstall --tenant cyclix
```

## Links

- Design: [docs/design/overview.md](docs/design/overview.md)
- The first build iteration: [docs/design/iteration-0.md](docs/design/iteration-0.md)
- The functional spec: the Gherkin feature files in `tests/features/`

## Licence

Apache-2.0. See [LICENSE](LICENSE).
