from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from autotube.domain.capabilities import Speech, SpeechRequest, SpeechSynthesizer
from autotube.domain.run_enums import LogLevel
from autotube.pipelines.narrated_video.settings.audio import NarrationCheck
from autotube.pipelines.narrated_video.text.error_rate import character_error_rate


@dataclass(frozen=True)
class CheckedSpeech:
    speech: Speech
    error_rate: float | None = None
    attempts: int = 1
    checked: bool = False


def checks_language(check: NarrationCheck, language: str) -> bool:
    return check.enabled and language.split("-")[0].lower() in check.languages


def heard_error_rate(speech: Speech, text: str) -> float | None:
    return character_error_rate(text, speech.transcript) if speech.transcript.strip() else None


def scored(speech: Speech, text: str, attempts: int) -> CheckedSpeech:
    return CheckedSpeech(speech, heard_error_rate(speech, text), attempts, checked=True)


def needs_retry(result: CheckedSpeech, check: NarrationCheck) -> bool:
    return result.error_rate is not None and result.error_rate > check.max_error_rate


def better(best: CheckedSpeech, candidate: CheckedSpeech) -> CheckedSpeech:
    improved = candidate.error_rate is not None and candidate.error_rate < (best.error_rate or 0.0)
    kept = candidate if improved else best
    return CheckedSpeech(kept.speech, kept.error_rate, candidate.attempts, checked=True)


def attempt_path(output: Path, attempt: int) -> Path:
    return output if attempt == 0 else output.with_name(f"{output.stem}-retry{attempt}.wav")


def checked_speech(
    tts: SpeechSynthesizer, request: SpeechRequest, output: Path, check: NarrationCheck
) -> CheckedSpeech:
    speech = tts.synthesize(request, output)
    if not checks_language(check, request.language):
        return CheckedSpeech(speech)
    best = scored(speech, request.text, 1)
    for attempt in range(1, check.retries + 1):
        if not needs_retry(best, check):
            break
        again = tts.synthesize(request, attempt_path(output, attempt))
        best = better(best, scored(again, request.text, attempt + 1))
    return best


def check_note(
    result: CheckedSpeech, check: NarrationCheck, line: str
) -> tuple[str, LogLevel] | None:
    if not result.checked:
        return None
    if result.error_rate is None:
        return f"narration check skipped for {line}: the voice gave no transcript", LogLevel.INFO
    summary = f"{line} error rate {result.error_rate:.2f} after {result.attempts} attempt(s)"
    if needs_retry(result, check):
        return f"{summary}, still above {check.max_error_rate:.2f}", LogLevel.WARNING
    return f"narration check {summary}", LogLevel.INFO
