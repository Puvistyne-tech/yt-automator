from __future__ import annotations

from dataclasses import dataclass

from autotube.application.automation_presenter import AutomationPresenter
from autotube.application.lookups import require_automation
from autotube.domain.automations import Automation, Target
from autotube.domain.copy_names import COPY_NAME_SUFFIX
from autotube.domain.ports import AutomationRepository, Clock, IdGenerator


@dataclass(frozen=True)
class DuplicateAutomation:
    automations: AutomationRepository
    presenter: AutomationPresenter
    ids: IdGenerator
    clock: Clock
    name_suffix: str = COPY_NAME_SUFFIX

    def execute(self, automation_id: str) -> Automation:
        source = require_automation(self.automations, automation_id)
        now = self.clock.now()
        copy = source.model_copy(
            update={
                "id": self.ids.new(),
                "name": f"{source.name}{self.name_suffix}",
                "enabled": False,
                "targets": tuple(self.copied_target(target) for target in source.targets),
                "created_at": now,
                "updated_at": now,
                "next_run_at": None,
                "last_run": None,
            }
        )
        self.automations.save(copy)
        return self.presenter.present(copy)

    def copied_target(self, target: Target) -> Target:
        return target.model_copy(update={"id": self.ids.new()})
