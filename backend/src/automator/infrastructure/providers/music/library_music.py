from __future__ import annotations

from pathlib import Path

from pydantic import Field

from automator.domain.capabilities import Capability, MusicRequest
from automator.infrastructure.providers.context import ProviderContext
from automator.infrastructure.providers.host import first_reason
from automator.infrastructure.providers.music.audio_fit import AudioFitOptions, fit_audio_command
from automator.infrastructure.providers.spec import ProviderSpec
from automator.infrastructure.providers.tts.word_alignment import normalised
from automator.shared.errors import UpstreamFailure
from automator.shared.hashing import sha256_hex

TRACK_SUFFIXES = frozenset({".mp3", ".wav", ".ogg", ".flac", ".m4a", ".opus"})


class LibraryMusicOptions(AudioFitOptions):
    folder: str = Field(
        default="",
        title="Music folder",
        description="Folder of CC0 tracks. Empty means <data dir>/assets/music.",
    )


def words_of(text: str) -> set[str]:
    return {normalised(word) for word in text.replace("_", " ").replace("-", " ").split()} - {""}


def pick_track(tracks: list[Path], prompt: str) -> Path:
    wanted = words_of(prompt)

    def rank(track: Path) -> tuple[int, str]:
        return -len(words_of(track.stem) & wanted), sha256_hex(f"{prompt}|{track.name}")

    return min(tracks, key=rank)


class LibraryMusic:
    provider_id = "library_music"

    def __init__(self, options: LibraryMusicOptions, context: ProviderContext) -> None:
        self.options = options
        self.context = context

    def folder(self) -> Path:
        return (
            Path(self.options.folder)
            if self.options.folder
            else self.context.data_dir / "assets" / "music"
        )

    def tracks(self) -> list[Path]:
        folder = self.folder()
        if not folder.is_dir():
            return []
        return sorted(path for path in folder.iterdir() if path.suffix.lower() in TRACK_SUFFIXES)

    def available(self) -> str | None:
        empty = None if self.tracks() else f"add CC0 music tracks to {self.folder()}"
        return first_reason(self.context.host.missing_binary(self.options.ffmpeg_binary), empty)

    def compose(self, request: MusicRequest, output: Path) -> Path:
        tracks = self.tracks()
        if not tracks:
            raise UpstreamFailure(f"no music tracks in {self.folder()}")
        output.parent.mkdir(parents=True, exist_ok=True)
        source = pick_track(tracks, request.prompt)
        command = fit_audio_command(source, output, request.duration_seconds, self.options)
        self.context.runner.run(command, self.options.timeout_seconds)
        return output


SPEC = ProviderSpec(
    provider_id=LibraryMusic.provider_id,
    capability=Capability.MUSIC,
    name="Music library",
    description="Picks one of your own CC0 tracks, looped or trimmed to length with fades.",
    options=LibraryMusicOptions,
    factory=LibraryMusic,
    offline=True,
)
