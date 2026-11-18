from __future__ import annotations

from dataclasses import dataclass

from automator.domain.capabilities import TimedClip, VideoComposition
from automator.infrastructure.providers.media.composition_inputs import InputPlan
from automator.infrastructure.providers.media.ffmpeg_options import FfmpegOptions


@dataclass(frozen=True)
class LoudnessMeasurement:
    integrated: float
    true_peak: float
    loudness_range: float
    threshold: float
    offset: float


def stereo(options: FfmpegOptions) -> str:
    return f"aresample={options.sample_rate},aformat=sample_fmts=fltp:channel_layouts=stereo"


def clip_chain(index: int, label: str, clip: TimedClip, options: FfmpegOptions) -> str:
    delay = round(clip.start_seconds * 1000)
    steps = [
        f"atrim=duration={clip.duration_seconds:.3f}",
        "asetpts=PTS-STARTPTS",
        stereo(options),
        f"volume={clip.volume:.3f}",
        f"adelay=delays={delay}:all=1",
    ]
    return f"[{index}:a]{','.join(steps)}[{label}]"


def mixed(labels: list[str], output: str) -> str:
    joined = "".join(f"[{label}]" for label in labels)
    return f"{joined}amix=inputs={len(labels)}:duration=longest:normalize=0[{output}]"


def music_chain(
    index: int, composition: VideoComposition, total: float, options: FfmpegOptions
) -> str:
    steps = [
        stereo(options),
        f"volume={composition.music_volume:.3f}",
        f"atrim=duration={total:.3f}",
    ]
    return f"[{index}:a]{','.join(steps)}[music]"


def ducking_chains(
    composition: VideoComposition, total: float, options: FfmpegOptions
) -> list[str]:
    ratio = 1 + composition.music_ducking * (options.duck_max_ratio - 1)
    compressor = (
        f"sidechaincompress=threshold={options.duck_threshold:g}:ratio={ratio:.2f}"
        f":attack={options.duck_attack_ms:g}:release={options.duck_release_ms:g}"
    )
    padded_voice = f"[voice]apad=whole_dur={total:.3f},asplit=2[voice_mix][voice_key]"
    return [padded_voice, f"[music][voice_key]{compressor}[bed]"]


def stem_chains(
    composition: VideoComposition, plan: InputPlan, total: float, options: FfmpegOptions
) -> tuple[list[str], list[str]]:
    chains: list[str] = []
    voices = [f"n{i}" for i in range(len(plan.narration))]
    effects = [f"e{i}" for i in range(len(plan.effects))]
    for label, index, clip in zip(voices, plan.narration, composition.narration, strict=True):
        chains.append(clip_chain(index, label, clip, options))
    for label, index, clip in zip(effects, plan.effects, composition.sound_effects, strict=True):
        chains.append(clip_chain(index, label, clip, options))
    stems = list(effects)
    if voices:
        chains.append(mixed(voices, "voice"))
    if plan.music is not None:
        chains.append(music_chain(plan.music, composition, total, options))
    if voices and plan.music is not None and composition.music_ducking > 0:
        chains.extend(ducking_chains(composition, total, options))
        return chains, ["voice_mix", "bed", *stems]
    return chains, [
        *(["voice"] if voices else []),
        *(["music"] if plan.music is not None else []),
        *stems,
    ]


def loudnorm(
    composition: VideoComposition, options: FfmpegOptions, measured: LoudnessMeasurement | None
) -> str:
    base = (
        f"loudnorm=I={composition.loudness_lufs:g}"
        f":TP={options.true_peak_db:g}:LRA={options.loudness_range:g}"
    )
    if measured is None:
        return base
    return (
        f"{base}:measured_I={measured.integrated:g}:measured_TP={measured.true_peak:g}"
        f":measured_LRA={measured.loudness_range:g}:measured_thresh={measured.threshold:g}"
        f":offset={measured.offset:g}:linear=true"
    )


def fades(composition: VideoComposition, total: float) -> list[str]:
    fade = min(composition.fade_seconds, total / 2)
    if fade <= 0:
        return []
    return [f"afade=t=in:st=0:d={fade:.3f}", f"afade=t=out:st={total - fade:.3f}:d={fade:.3f}"]


def audio_graph(
    composition: VideoComposition,
    plan: InputPlan,
    total: float,
    options: FfmpegOptions,
    level: str | None,
) -> list[str]:
    chains, stems = stem_chains(composition, plan, total, options)
    if not stems:
        silence = f"anullsrc=r={options.sample_rate}:cl=stereo,atrim=duration={total:.3f}[aout]"
        return [*chains, silence]
    chains.append(mixed(stems, "mix"))
    steps = [
        f"apad=whole_dur={total:.3f}",
        f"atrim=duration={total:.3f}",
        *fades(composition, total),
    ]
    if level:
        steps += [level, stereo(options)]
    return [*chains, f"[mix]{','.join(steps)}[aout]"]
