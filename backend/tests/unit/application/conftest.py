from __future__ import annotations

import pytest

from tests.fixtures.harness import Harness
from tests.fixtures.template_rig import TemplateRig


@pytest.fixture
def rig(harness: Harness) -> TemplateRig:
    return TemplateRig(harness)
