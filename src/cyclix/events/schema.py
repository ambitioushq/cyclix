"""Event schema version 0, as fixed in docs/design/iteration-0.md, "The event log, schema version 0".

Any change here is made in that doc first.
"""

SCHEMA = "cyclix.event/0"
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
ROUND = "cyclix.round"
TRUST_LEVEL = "cyclix.trust_level"
CONFIG_VERSION = "cyclix.config.version"
DURATION_MS = "cyclix.duration_ms"
COST_USD = "cyclix.cost.usd"
# The decimal places kept in COST_USD, as fixed in the design doc under "The event log, schema version 0".
COST_PLACES = 6
REPOSITORY_URL = "vcs.repository.url.full"
HEAD_NAME = "vcs.ref.head.name"
HEAD_REVISION = "vcs.ref.head.revision"
CHANGE_ID = "vcs.change.id"
MODEL = "gen_ai.request.model"
INPUT_TOKENS = "gen_ai.usage.input_tokens"
OUTPUT_TOKENS = "gen_ai.usage.output_tokens"
GATE_CHECKS = "cyclix.gate.checks"

# Every stage-run event has exactly these keys, in this order. A key with no value is null.
STAGE_RUN_KEYS = (
    TENANT,
    ISSUE_ID,
    RUN_ID,
    STAGE,
    OUTCOME,
    OUTCOME_REASON,
    ROUND,
    TRUST_LEVEL,
    CONFIG_VERSION,
    DURATION_MS,
    COST_USD,
    REPOSITORY_URL,
    HEAD_NAME,
    HEAD_REVISION,
    CHANGE_ID,
    MODEL,
    INPUT_TOKENS,
    OUTPUT_TOKENS,
    GATE_CHECKS,
)

STAGES = ("admission", "plan", "build", "gate", "adversarial_review", "pr", "reconciler")
OUTCOMES = ("passed", "parked", "stopped", "failed", "crashed", "skipped")
