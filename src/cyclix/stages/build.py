"""The minimal build stage: one agent call in the worktree that leaves its work committed.

The agent's final answer becomes the PR body. The stage saves it as pr.md in the run folder.
"""

from cyclix.events import schema
from cyclix.stages.base import StageResult, call_agent, prompt

TEMPLATE = (".github", "pull_request_template.md")

ANSWER_IS_THE_BODY = (
    "Your final answer becomes the pull request body word for word. "
    "Write nothing before it and nothing after it."
)


def pr_instructions(ctx):
    """What the agent is asked to answer with: the tenant's PR template, or a short summary."""
    number = ctx.issue.number
    path = ctx.worktree.path.joinpath(*TEMPLATE)
    if path.is_file():
        return (
            f"{ANSWER_IS_THE_BODY} End with this template filled in as your answer, "
            f"with `Closes #{number}` on its first line:\n\n{path.read_text()}"
        )
    return (
        f"{ANSWER_IS_THE_BODY} Start it with `Closes #{number}` on its first line, "
        "then give a short plain summary of what changed."
    )


class Build:
    name = "build"

    def run(self, ctx):
        issue = ctx.issue
        plan = (ctx.run_dir / "plan.md").read_text()
        text = prompt(
            "build",
            number=issue.number,
            title=issue.title,
            body=issue.body,
            plan=plan,
            tools="\n".join(f"- {rule}" for rule in ctx.config.agent.build.tools),
            pr_instructions=pr_instructions(ctx),
        )
        before = ctx.codehost.head_sha(ctx.worktree)
        result, fields = call_agent(ctx, text, ctx.config.agent.build)
        after = ctx.codehost.head_sha(ctx.worktree)
        fields[schema.HEAD_REVISION] = after
        if result.is_error:
            return StageResult("failed", f"agent: {result.reason}", fields)
        if after == before:
            return StageResult("failed", "the agent made no commit", fields)
        (ctx.run_dir / "pr.md").write_text(result.answer.strip() + "\n")
        return StageResult("passed", fields=fields)
