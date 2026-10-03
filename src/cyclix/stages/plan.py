"""The minimal plan stage: one agent call that writes plan.md in the run folder.

An answer that starts with "STOP:" stops the run, and the rest of that line is the reason.
"""

from cyclix.stages.base import StageResult, call_agent, prompt

STOP = "STOP:"


class Plan:
    name = "plan"

    def run(self, ctx):
        issue = ctx.issue
        text = prompt("plan", number=issue.number, title=issue.title, body=issue.body)
        result, fields = call_agent(ctx, text, ctx.config.agent.model_plan)
        if result.is_error:
            return StageResult("failed", f"agent: {result.reason}", fields)
        answer = result.answer.strip()
        if answer.startswith(STOP):
            reason = answer.removeprefix(STOP).splitlines()[0].strip() if answer != STOP else ""
            return StageResult("stopped", reason or "the agent stopped without a reason", fields)
        if not answer:
            return StageResult("failed", "the agent's plan was empty", fields)
        (ctx.run_dir / "plan.md").write_text(answer + "\n")
        return StageResult("passed", fields=fields)
