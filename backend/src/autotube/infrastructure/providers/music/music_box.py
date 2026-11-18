from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from autotube.infrastructure.providers.wav_io import Samples

PENTATONIC = (0, 2, 4, 7, 9, 12, 14, 16)
PROGRESSIONS = ((0, 7, 9, 5), (0, 5, 7, 0), (0, 9, 5, 7), (0, 5, 9, 7))
MINOR_ROOTS = frozenset({9, 4, 2})


@dataclass(frozen=True)
class MusicBoxTuning:
    sample_rate: int
    tempo_bpm: float
    volume: float
    fade_seconds: float
    pad_level: float
    chime_level: float
    note_density: float


def frequency(midi: float) -> float:
    return float(440.0 * 2 ** ((midi - 69) / 12))


def triad(root: int, offset: int) -> tuple[int, int, int]:
    third = 3 if offset % 12 in MINOR_ROOTS else 4
    base = root + offset
    return base, base + third, base + 7


def place(track: Samples, start: int, sound: Samples, pan: float) -> None:
    if start < 0:
        sound, start = sound[-start:], 0
    end = min(len(track), start + len(sound))
    if end <= start:
        return
    piece = sound[: end - start]
    track[start:end, 0] += piece * (1 - pan) / 2
    track[start:end, 1] += piece * (1 + pan) / 2


def pad_chord(notes: tuple[int, int, int], seconds: float, rate: int) -> Samples:
    clock = np.arange(round(seconds * rate)) / rate
    tone = sum(np.sin(2 * np.pi * frequency(note - 12) * clock) for note in notes)
    swell = np.sin(np.pi * np.clip(clock / seconds, 0, 1)) ** 2
    return np.asarray(tone * swell / 3, dtype=np.float64)


def chime(note: int, rate: int, seconds: float = 1.6) -> Samples:
    clock = np.arange(round(seconds * rate)) / rate
    pitch = frequency(note)
    body = np.sin(2 * np.pi * pitch * clock) + 0.35 * np.sin(4 * np.pi * pitch * clock)
    sparkle = 0.12 * np.sin(6 * np.pi * pitch * clock) * np.exp(-clock * 9)
    attack = np.clip(clock / 0.004, 0, 1)
    return np.asarray((body + sparkle) * np.exp(-clock * 3.2) * attack, dtype=np.float64)


def lay_pad(
    track: Samples, root: int, progression: tuple[int, ...], tuning: MusicBoxTuning
) -> None:
    bar = 240.0 / tuning.tempo_bpm
    rate = tuning.sample_rate
    for index in range(int(len(track) / rate / bar) + 1):
        notes = triad(root, progression[index % len(progression)])
        sound = pad_chord(notes, bar * 1.5, rate) * tuning.pad_level
        place(track, round((index * bar - bar * 0.25) * rate), sound, 0.0)


def lay_chimes(
    track: Samples,
    root: int,
    progression: tuple[int, ...],
    tuning: MusicBoxTuning,
    rng: np.random.Generator,
) -> None:
    step = 30.0 / tuning.tempo_bpm
    rate = tuning.sample_rate
    for index in range(int(len(track) / rate / step)):
        if rng.random() > tuning.note_density:
            continue
        chord_root = progression[(index // 8) % len(progression)]
        note = root + chord_root % 12 + int(rng.choice(PENTATONIC))
        sound = chime(note, rate) * tuning.chime_level
        place(track, round(index * step * rate), sound, float(rng.uniform(-0.6, 0.6)))


def faded(track: Samples, tuning: MusicBoxTuning) -> Samples:
    count = len(track)
    fade = min(round(tuning.fade_seconds * tuning.sample_rate), count // 2)
    envelope = np.ones(count)
    if fade > 0:
        ramp = np.linspace(0.0, 1.0, fade)
        envelope[:fade] = ramp
        envelope[count - fade :] = ramp[::-1]
    return track * envelope[:, None]


def render_music_box(seed: int, duration_seconds: float, tuning: MusicBoxTuning) -> Samples:
    rng = np.random.default_rng(seed)
    root = 57 + int(rng.integers(0, 8))
    progression = PROGRESSIONS[int(rng.integers(0, len(PROGRESSIONS)))]
    track = np.zeros((max(1, round(duration_seconds * tuning.sample_rate)), 2))
    lay_pad(track, root, progression, tuning)
    lay_chimes(track, root, progression, tuning, rng)
    peak = float(np.max(np.abs(track))) or 1.0
    return faded(track / peak * tuning.volume, tuning)
