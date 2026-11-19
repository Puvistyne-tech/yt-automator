from __future__ import annotations

AMERICAN_VOICES = (
    "af_heart af_alloy af_aoede af_bella af_jessica af_kore af_nicole af_nova af_river af_sarah "
    "af_sky am_adam am_echo am_eric am_fenrir am_liam am_michael am_onyx am_puck am_santa"
)
BRITISH_VOICES = "bf_alice bf_emma bf_isabella bf_lily bm_daniel bm_fable bm_george bm_lewis"
OTHER_VOICES = "hf_alpha hf_beta hm_omega hm_psi ef_dora em_alex em_santa ff_siwis"


def kokoro_voice_ids() -> list[str]:
    return f"{AMERICAN_VOICES} {BRITISH_VOICES} {OTHER_VOICES}".split()
