from __future__ import annotations

import sys

import pytest

from automator.infrastructure.providers.process import SubprocessRunner
from automator.shared.errors import UpstreamFailure

pytestmark = pytest.mark.integration


def test_runner_returns_output_and_passes_stdin_and_env() -> None:
    script = "import os, sys; print(sys.stdin.read() + os.environ['PROBE'])"
    result = SubprocessRunner().run(
        [sys.executable, "-c", script], 30, stdin="hi ", env={"PROBE": "x"}
    )
    assert result.stdout.strip() == "hi x"


def test_runner_reports_the_tail_of_stderr_on_failure() -> None:
    script = "import sys; sys.stderr.write('a' * 5000 + 'the end'); sys.exit(3)"
    with pytest.raises(UpstreamFailure) as raised:
        SubprocessRunner(stderr_tail_chars=20).run([sys.executable, "-c", script], 30)
    assert raised.value.code == "tool_failed"
    assert raised.value.message.endswith("exited with 3: aaaaaaaaaaaaathe end")


def test_runner_converts_missing_binaries_and_timeouts() -> None:
    with pytest.raises(UpstreamFailure) as missing:
        SubprocessRunner().run(["definitely-not-a-binary-xyz"], 5)
    assert missing.value.code == "tool_missing"
    with pytest.raises(UpstreamFailure) as slow:
        SubprocessRunner().run([sys.executable, "-c", "import time; time.sleep(5)"], 0.2)
    assert slow.value.code == "tool_timeout"
