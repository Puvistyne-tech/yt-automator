from __future__ import annotations

import pytest

from automator.domain.channels import ChannelDefaults, Privacy
from automator.domain.kids_rules import (
    effective_made_for_kids,
    effective_privacy,
    enforce_kids_content,
)
from tests.fixtures.builders import target_input
from tests.fixtures.fake_pipeline import FakePipeline, kids_pipeline

REGULAR = FakePipeline().descriptor
KIDS = kids_pipeline().descriptor


def test_kids_pipeline_forces_made_for_kids_on_every_target() -> None:
    targets = (target_input(), target_input(made_for_kids=False))
    assert [t.made_for_kids for t in enforce_kids_content(targets, KIDS)] == [True, True]
    assert [t.made_for_kids for t in enforce_kids_content(targets, REGULAR)] == [None, False]


@pytest.mark.parametrize(
    ("target_value", "channel_value", "kids", "expected"),
    [
        (None, False, False, False),
        (None, True, False, True),
        (True, False, False, True),
        (False, True, False, False),
        (False, False, True, True),
        (None, False, True, True),
    ],
)
def test_effective_made_for_kids(
    target_value: bool | None, channel_value: bool, kids: bool, expected: bool
) -> None:
    target = target_input(made_for_kids=target_value)
    defaults = ChannelDefaults(made_for_kids=channel_value)
    descriptor = KIDS if kids else REGULAR
    assert effective_made_for_kids(target, defaults, descriptor) is expected


def test_missing_descriptor_falls_back_to_target_and_channel() -> None:
    assert effective_made_for_kids(target_input(), ChannelDefaults(made_for_kids=True), None)


@pytest.mark.parametrize(
    ("target_value", "expected"),
    [
        (None, Privacy.UNLISTED),
        (Privacy.PUBLIC, Privacy.PUBLIC),
        (Privacy.PRIVATE, Privacy.PRIVATE),
    ],
)
def test_effective_privacy(target_value: Privacy | None, expected: Privacy) -> None:
    defaults = ChannelDefaults(privacy=Privacy.UNLISTED)
    assert effective_privacy(target_input(privacy=target_value), defaults) is expected


def test_channel_defaults_are_safe() -> None:
    defaults = ChannelDefaults()
    assert defaults.privacy is Privacy.PRIVATE and not defaults.notify_subscribers
