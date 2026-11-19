from __future__ import annotations

from autotube.domain.capabilities import Capability
from autotube.domain.provider_fallbacks import (
    ProviderFallback,
    fallback_warnings,
    short_reason,
    stand_in_sources,
    without_secrets,
)

GATED = "GatedRepoError: 403 Client Error.\nCannot access gated repo for url https://hf.co/x"


def fell_back(
    failed: str = "mflux", used: str = "offline_image", reason: str = GATED
) -> ProviderFallback:
    return ProviderFallback(capability=Capability.IMAGE, failed=failed, used=used, reason=reason)


def test_short_reason_keeps_the_first_line_within_the_limit() -> None:
    assert short_reason(GATED, 200) == "GatedRepoError: 403 Client Error."
    assert short_reason("abcdefghij", 5) == "abcd…"
    assert short_reason("abcde", 5) == "abcde"
    assert short_reason("\n\n", 200) == "no reason given"


def test_without_secrets_masks_every_known_value() -> None:
    assert without_secrets("Bearer sk-123 and sk-123", ["sk-123", ""]) == (
        "Bearer [secret] and [secret]"
    )


def test_fallback_warnings_group_repeated_calls() -> None:
    warnings = fallback_warnings([fell_back(), fell_back(), fell_back("comfy", reason="down")], 200)
    assert warnings == [
        "image provider mflux failed (GatedRepoError: 403 Client Error.); "
        "used offline_image instead for 2 calls",
        "image provider comfy failed (down); used offline_image instead",
    ]
    assert fallback_warnings([], 200) == []


def test_grouped_warnings_keep_the_earliest_reason() -> None:
    warnings = fallback_warnings([fell_back(reason="first"), fell_back(reason="second")], 200)
    assert warnings == [
        "image provider mflux failed (first); used offline_image instead for 2 calls"
    ]


def test_stand_in_sources_name_the_providers_a_picture_replaced() -> None:
    fallbacks = [fell_back(), fell_back("comfy"), fell_back("mflux"), fell_back(used="other")]
    speech = ProviderFallback(
        capability=Capability.TTS, failed="kokoro", used="offline_image", reason="x"
    )
    assert stand_in_sources([*fallbacks, speech], Capability.IMAGE, "offline_image") == [
        "comfy",
        "mflux",
    ]
    assert stand_in_sources(fallbacks, Capability.IMAGE, "mflux") == []
