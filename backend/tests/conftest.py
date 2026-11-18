from __future__ import annotations

from pathlib import Path

import pytest

from automator.domain.automations import Automation
from automator.domain.channels import Channel
from automator.domain.credentials import Credential
from tests.fixtures.builders import add_automation, add_channel, add_credential
from tests.fixtures.harness import Harness


@pytest.fixture
def harness(tmp_path: Path) -> Harness:
    return Harness(root=tmp_path / "artifacts")


@pytest.fixture
def credential(harness: Harness) -> Credential:
    return add_credential(harness)


@pytest.fixture
def channel(harness: Harness, credential: Credential) -> Channel:
    return add_channel(harness, credential_id=credential.id)


@pytest.fixture
def automation(harness: Harness) -> Automation:
    return add_automation(harness)
