from __future__ import annotations

from pathlib import Path

from automator.shared.errors import RuleConflict


class SecretsUnreadable(RuleConflict):
    def __init__(self, message: str) -> None:
        super().__init__("secrets_unreadable", message)


def file_unreadable(path: Path, key_path: Path) -> SecretsUnreadable:
    return SecretsUnreadable(
        f"the secrets file {path} cannot be decrypted with its key {key_path}; remove both "
        "files, then reconnect your channels and enter your credentials and API keys again"
    )


def keychain_unreadable(failure: Exception) -> SecretsUnreadable:
    return SecretsUnreadable(
        f"the keychain cannot be used ({type(failure).__name__}); unlock the login keychain "
        "or allow YouTube Automator to access it, then try again"
    )
