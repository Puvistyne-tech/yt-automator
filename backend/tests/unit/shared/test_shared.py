from __future__ import annotations

from datetime import UTC, datetime, timedelta, timezone

import pytest

from autotube.shared.clock import (
    find_zone,
    is_valid_timezone,
    local_date,
    local_day_start,
    require_aware,
    to_iso,
    to_utc,
    utc_now,
)
from autotube.shared.errors import NotFound, RuleConflict, UpstreamFailure, ValidationFailed
from autotube.shared.hashing import hmac_sha256_hex, same_digest, sha256_hex, stable_hash
from autotube.shared.ids import is_opaque_id, random_id
from autotube.shared.signed_tokens import read_unverified, sign_payload, verify_signature


def test_error_hierarchy_carries_code_message_and_fields() -> None:
    missing = NotFound("run", "r1")
    invalid = ValidationFailed({"name": "required"})
    conflict = RuleConflict("channel_in_use", "busy")
    upstream = UpstreamFailure("google down")
    assert (missing.code, missing.entity, missing.entity_id) == ("run_not_found", "run", "r1")
    assert invalid.code == "validation_failed" and invalid.fields == {"name": "required"}
    assert (conflict.code, conflict.message, conflict.fields) == ("channel_in_use", "busy", {})
    assert (upstream.code, str(upstream)) == ("upstream_failure", "google down")


def test_utc_helpers_reject_naive_and_normalise() -> None:
    plus_two = datetime(2026, 1, 1, 12, tzinfo=timezone(timedelta(hours=2)))
    assert to_utc(plus_two) == datetime(2026, 1, 1, 10, tzinfo=UTC)
    assert to_iso(plus_two) == "2026-01-01T10:00:00+00:00"
    assert utc_now().tzinfo is UTC
    with pytest.raises(ValueError, match="timezone-aware"):
        require_aware(datetime(2026, 1, 1))


@pytest.mark.parametrize(
    ("name", "valid"), [("UTC", True), ("Asia/Kolkata", True), ("Mars/Base", False), ("", False)]
)
def test_timezone_validation(name: str, valid: bool) -> None:
    assert is_valid_timezone(name) is valid
    assert (find_zone(name) is not None) is valid


def test_local_day_boundaries_follow_the_zone() -> None:
    moment = datetime(2026, 3, 1, 2, 0, tzinfo=UTC)
    assert local_date(moment, "America/Los_Angeles").isoformat() == "2026-02-28"
    assert local_day_start(moment, "Asia/Kolkata") == datetime(2026, 2, 28, 18, 30, tzinfo=UTC)


def test_hashing_is_stable_and_keyed() -> None:
    assert sha256_hex("abc") == sha256_hex(b"abc")
    assert stable_hash({"b": 1, "a": 2}) == stable_hash({"a": 2, "b": 1})
    assert hmac_sha256_hex("k", "m") != hmac_sha256_hex("other", "m")
    assert same_digest("aa", "aa") and not same_digest("aa", "ab")


def test_random_ids_are_unique_and_opaque() -> None:
    first, second = random_id(), random_id("run")
    assert first != second and second.startswith("run_")
    assert is_opaque_id(first) and not is_opaque_id("has space")


def test_signed_tokens_round_trip_and_detect_tampering() -> None:
    token = sign_payload({"credential_id": "c1"}, "key")
    assert read_unverified(token) == {"credential_id": "c1"}
    assert verify_signature(token, "key")
    assert not verify_signature(token, "wrong")
    assert not verify_signature(token.replace(".", ".x", 1), "key")


@pytest.mark.parametrize("token", ["", "no-separator", "!!!.sig", "WzFd.sig"])
def test_malformed_tokens_are_unreadable(token: str) -> None:
    assert read_unverified(token) is None
    assert not verify_signature(token, "key")
