from __future__ import annotations

from datetime import timedelta
from typing import Any

from automator.domain.automations import Automation, Target
from automator.domain.channels import Channel, ChannelDefaults, Privacy
from automator.domain.credentials import Credential
from automator.domain.quality import ScoreItem
from automator.domain.run_enums import ArtifactKind
from automator.domain.run_parts import Artifact, StageRun
from automator.domain.runs import Run
from automator.domain.schedules import Schedule, ScheduleKind
from tests.fixtures.fake_runtime import START


def credential(credential_id: str = "cred-1") -> Credential:
    return Credential(id=credential_id, name="Project", client_id="client", created_at=START)


def channel(channel_id: str = "chan-1", youtube_id: str = "UC-1") -> Channel:
    return Channel(
        id=channel_id,
        credential_id="cred-1",
        youtube_channel_id=youtube_id,
        title="Kids",
        defaults=ChannelDefaults(privacy=Privacy.UNLISTED, made_for_kids=True),
        connected_at=START,
    )


def automation() -> Automation:
    return Automation(
        id="auto-1",
        name="Bedtime",
        pipeline_type="fake",
        settings={"topic": "owls", "nested": {"list": [1, 2.5, None]}},
        languages=("en", "ta"),
        targets=(Target(id="t-1", channel_id="chan-1", language="en", variants=("short",)),),
        schedule=Schedule(kind=ScheduleKind.CRON, cron="0 9 * * *", timezone="Asia/Kolkata"),
        created_at=START,
        updated_at=START + timedelta(minutes=5),
    )


def run(run_id: str, minutes: int = 0, **changes: Any) -> Run:
    base = Run(
        id=run_id,
        automation_id="auto-1",
        automation_name="Bedtime",
        pipeline_type="fake",
        languages=("en",),
        settings_snapshot={"topic": "owls"},
        stages=(StageRun(stage_id="script", title="Script"),),
        artifacts=(
            Artifact(
                id="a-1",
                kind=ArtifactKind.VIDEO,
                stage_id="script",
                filename="en.mp4",
                media_type="video/mp4",
                size_bytes=3,
                meta={"seconds": 1.5},
            ),
        ),
        score=91.5,
        score_details=(ScoreItem(id="q", title="Quality", score=91.5),),
        created_at=START + timedelta(minutes=minutes),
    )
    return base.model_copy(update=changes)
