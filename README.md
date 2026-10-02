# Cyclix

Cyclix runs an unattended issue-to-PR loop. It takes a well-formed issue from a board, plans the change, builds it, runs the quality gate, reviews it adversarially, opens a pull request, and carries that PR to a human merge. A person reviews and merges every PR.

**Pre-release. Not ready for use.** The code is written in public from the first commit. Interfaces will change without notice until v0.1.

- Design: [docs/design/overview.md](docs/design/overview.md)
- The first build iteration: [docs/design/iteration-0.md](docs/design/iteration-0.md)
- The functional spec: the Gherkin feature files in `tests/features/`

## Licence

Apache-2.0. See [LICENSE](LICENSE).
