---
title: Turn on shell completion
---

Shell completion lets the Tab key complete `cyclix`'s commands and flags in bash, zsh and fish. It needs the optional `extras` group, which installs [argcomplete](https://github.com/kislyuk/argcomplete). A plain install of Cyclix leaves it out (see [ADR-0008](/adr/0008-offer-shell-completion-through-an-optional-argcomplete-extra/)).

1. Install Cyclix with the `extras` group, and put argcomplete's `register-python-argcomplete` command on your `PATH`:

   ```sh
   uv tool install --with-executables-from argcomplete "cyclix[extras] @ git+https://github.com/ambitioushq/cyclix"
   ```

   With `pipx`, run `pipx install --include-deps "cyclix[extras] @ git+https://github.com/ambitioushq/cyclix"`.

2. Register `cyclix` with your shell:

   | Shell | What to do |
   | --- | --- |
   | bash | Add `eval "$(register-python-argcomplete cyclix)"` to `~/.bashrc`. |
   | zsh | Add `eval "$(register-python-argcomplete cyclix)"` to `~/.zshrc`, after the line that runs `compinit`. |
   | fish | Run `mkdir -p ~/.config/fish/completions`, then `register-python-argcomplete --shell fish cyclix > ~/.config/fish/completions/cyclix.fish`, once. |

3. Open a new shell.
