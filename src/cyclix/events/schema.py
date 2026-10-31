"""Event schema version 1: the keys and values a stage-run event may hold.

Any change here is made in the design doc's event log section first.
"""

SCHEMA = "cyclix.event/1"
SERVICE_NAME = "cyclix"

STAGE_RUN = "stage_run"

# The longest string an attribute may hold. A longer one is most likely prompt or
# code text that belongs in the run folder, not the event log.
MAX_STRING = 500

TENANT = "cyclix.tenant"
ISSUE_ID = "cyclix.issue.id"
RUN_ID = "cyclix.run.id"
STAGE = "cyclix.stage"
OUTCOME = "cyclix.outcome"
OUTCOME_REASON = "cyclix.outcome.reason"
CONFIG_VERSION = "cyclix.config.version"
INSTRUCTIONS_VERSION = "cyclix.agent.instructions.version"
DURATION_MS = "cyclix.duration_ms"
COST_USD = "cyclix.cost.usd"
# The decimal places kept in COST_USD: a millionth of a dollar. Past that, the agent's costs are float noise.
COST_PLACES = 6
REPOSITORY_URL = "vcs.repository.url.full"
HEAD_NAME = "vcs.ref.head.name"
HEAD_REVISION = "vcs.ref.head.revision"
CHANGE_ID = "vcs.change.id"
MODEL = "gen_ai.request.model"
INPUT_TOKENS = "gen_ai.usage.input_tokens"
OUTPUT_TOKENS = "gen_ai.usage.output_tokens"
AGENT_TURNS = "cyclix.agent.turns"
GATE_CHECKS = "cyclix.gate.checks"

# Every stage-run event has exactly these keys, in this order. A key with no value is null.
STAGE_RUN_KEYS = (
    TENANT,
    ISSUE_ID,
    RUN_ID,
    STAGE,
    OUTCOME,
    OUTCOME_REASON,
    CONFIG_VERSION,
    INSTRUCTIONS_VERSION,
    DURATION_MS,
    COST_USD,
    REPOSITORY_URL,
    HEAD_NAME,
    HEAD_REVISION,
    CHANGE_ID,
    MODEL,
    INPUT_TOKENS,
    OUTPUT_TOKENS,
    AGENT_TURNS,
    GATE_CHECKS,
)

STAGES = ("admission", "plan", "build", "gate", "pr", "reconciler")
OUTCOMES = ("passed", "parked", "stopped", "failed", "crashed")
