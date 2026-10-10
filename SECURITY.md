# Security

## Reporting

Report a vulnerability through GitHub's private vulnerability reporting on this repository. Do not open a public issue for it.

## Threat model

Cyclix runs a coding agent unattended against a repository, with the right to push branches and open pull requests. The main risks:

- **Prompt injection through text the agent reads.** Issue bodies, comments, PR reviews and file contents can carry instructions. Cyclix admits work only from items a maintainer places on the board, and ignores issues and comments from anyone outside the configured maintainers. An agent still reads repository content, so a malicious file already merged can steer it.
- **Secrets the agent can reach.** Today the agent and the gate run as the host user, with the host user's environment, so they can read that user's files, `gh` login included. Run Cyclix as a dedicated user that holds only the tokens the loop needs. The design in `docs/design/isolation.md` runs the agent and the gate in a container that holds no GitHub credential, behind a network allow list, with the engine doing every push itself. It is being built in stages, and that document says which stages are done.
- **Pushing harmful code.** Cyclix never merges. Every PR waits for a human review and merge, and the repository's branch protection is the final gate.
- **Leaking private names into a public record.** The event log holds IDs and numbers only, never code, prompts or issue text.
- **Supply chain.** The runtime uses the Python standard library by default. Each runtime dependency needs a written reason in the design docs.
