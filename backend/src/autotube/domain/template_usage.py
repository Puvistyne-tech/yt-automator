from __future__ import annotations

from collections.abc import Iterable, Sequence

from autotube.domain.automations import Automation
from autotube.domain.run_enums import RunStatus
from autotube.domain.run_state import is_unfinished_run
from autotube.domain.runs import Run
from autotube.shared.errors import RuleConflict

UNPUBLISHED_STATUSES = frozenset({RunStatus.AWAITING_REVIEW, RunStatus.APPROVED})


def is_open_run(run: Run) -> bool:
    return run.status in UNPUBLISHED_STATUSES or is_unfinished_run(run)


def automations_using(type_id: str, automations: Iterable[Automation]) -> list[str]:
    return sorted(a.name for a in automations if a.pipeline_type == type_id)


def runs_using(type_id: str, runs: Iterable[Run]) -> list[str]:
    return sorted(run.id for run in runs if run.pipeline_type == type_id and is_open_run(run))


def template_in_use(automations: Sequence[str], runs: Sequence[str], remedy: str) -> RuleConflict:
    users = [
        f"{kind}: {', '.join(names)}"
        for kind, names in (("automations", automations), ("open runs", runs))
        if names
    ]
    return RuleConflict("template_in_use", f"template is used by {' and '.join(users)}; {remedy}")


def ensure_unused(
    type_id: str, automations: Iterable[Automation], runs: Iterable[Run], remedy: str
) -> None:
    using = automations_using(type_id, automations)
    open_runs = runs_using(type_id, runs)
    if using or open_runs:
        raise template_in_use(using, open_runs, remedy)
