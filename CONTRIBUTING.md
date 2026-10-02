# Contributing

Cyclix has one maintainer, who writes the code. Pull requests from others are not accepted.

**Bug reports are welcome.** Open an issue with what you ran, what you expected, and what happened. Leave out secrets, tokens and private repository names.

GitHub Discussions open with the v0.1 release.

Issues filed by anyone other than the maintainer are never picked up by the loop that builds Cyclix. The maintainer reads them and decides what becomes work.

## The names check

The repository is public. A CI job, `names`, fails any change whose files or commit messages contain a name from a private list. The list is kept outside the repository. To run the check locally, set `CYCLIX_FORBIDDEN_NAMES` and run `python3 scripts/names_check.py`.
