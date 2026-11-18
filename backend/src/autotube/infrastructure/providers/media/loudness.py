from __future__ import annotations

import json
import math
import re

from autotube.infrastructure.providers.media.composition_audio import LoudnessMeasurement
from autotube.shared.errors import UpstreamFailure

INTEGRATED = re.compile(r"I:\s+(-?\d+(?:\.\d+)?|-inf)\s+LUFS")
JSON_BLOCK = re.compile(r"\{[^{}]*\"input_i\"[^{}]*\}", re.DOTALL)


def as_number(value: object) -> float:
    try:
        return float(str(value))
    except ValueError:
        return -math.inf


def parse_loudnorm(stderr: str) -> LoudnessMeasurement | None:
    blocks = JSON_BLOCK.findall(stderr)
    if not blocks:
        raise UpstreamFailure("ffmpeg printed no loudness measurement")
    values = json.loads(blocks[-1])
    measurement = LoudnessMeasurement(
        integrated=as_number(values.get("input_i")),
        true_peak=as_number(values.get("input_tp")),
        loudness_range=as_number(values.get("input_lra")),
        threshold=as_number(values.get("input_thresh")),
        offset=as_number(values.get("target_offset")),
    )
    finite = all(
        math.isfinite(number)
        for number in (measurement.integrated, measurement.true_peak, measurement.threshold)
    )
    return measurement if finite else None


def parse_integrated(stderr: str) -> float:
    found = INTEGRATED.findall(stderr)
    if not found:
        raise UpstreamFailure("ffmpeg printed no integrated loudness")
    return as_number(found[-1])
