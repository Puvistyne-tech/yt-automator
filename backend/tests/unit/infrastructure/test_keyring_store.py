from __future__ import annotations

import pytest

from autotube.infrastructure.secrets.unreadable import SecretsUnreadable
from tests.fixtures.fake_keyring import locked_store


@pytest.mark.parametrize("action", ["get", "has", "set", "delete"])
def test_a_locked_keychain_raises_secrets_unreadable(action: str) -> None:
    arguments = ("api", "value-123") if action == "set" else ("api",)
    with pytest.raises(SecretsUnreadable, match="KeyringLocked") as raised:
        getattr(locked_store(), action)(*arguments)
    assert raised.value.code == "secrets_unreadable"
    assert "value-123" not in raised.value.message
