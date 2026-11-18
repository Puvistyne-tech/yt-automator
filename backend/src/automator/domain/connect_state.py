from __future__ import annotations

from datetime import datetime, timedelta

from pydantic import AwareDatetime, Field

from automator.domain.model_base import DomainModel
from automator.shared.clock import to_utc
from automator.shared.errors import ValidationFailed
from automator.shared.signed_tokens import read_unverified, sign_payload, verify_signature


class ConnectStatePolicy(DomainModel):
    max_age_minutes: int = Field(default=15, ge=1)


class ConnectState(DomainModel):
    credential_id: str
    nonce: str
    issued_at: AwareDatetime


def invalid_state(reason: str) -> ValidationFailed:
    return ValidationFailed({"state": reason}, "invalid OAuth state")


def issue_state(state: ConnectState, key: str) -> str:
    payload = {
        "credential_id": state.credential_id,
        "nonce": state.nonce,
        "issued_at": to_utc(state.issued_at).isoformat(),
    }
    return sign_payload(payload, key)


def read_state(token: str) -> ConnectState:
    payload = read_unverified(token)
    if payload is None or set(payload) != {"credential_id", "nonce", "issued_at"}:
        raise invalid_state("malformed")
    try:
        return ConnectState.model_validate(payload)
    except ValueError as error:
        raise invalid_state("malformed") from error


def verify_state(
    token: str, state: ConnectState, key: str, now: datetime, policy: ConnectStatePolicy
) -> None:
    if not verify_signature(token, key):
        raise invalid_state("signature mismatch")
    age = to_utc(now) - to_utc(state.issued_at)
    if age > timedelta(minutes=policy.max_age_minutes) or age < timedelta(0):
        raise invalid_state("expired")
