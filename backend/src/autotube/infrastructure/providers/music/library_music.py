from __future__ import annotations

from pathlib import Path

from pydantic import Field

from autotube.domain.capabilities import Capability, MusicRequest
from autotube.infrastructure.providers.context import ProviderContext
from autotube.infrastructure.providers.host import first_reason
from autotube.infrastructure.providers.music.audio_fit import AudioFitOptions, fit_audio_command
from autotube.infrastructure.providers.output_path import ensure_parent
from autotube.infrastructure.providers.spec import ProviderSpec
from autotube.infrastructure.providers.word_normalisation import normalised
from autotube.shared.errors import UpstreamFailure
from autotube.shared.hashing import sha256_hex

TRACK_SUFFIXES = frozenset({".mp3", ".wav", ".ogg", ".flac", ".m4a", ".opus"})


class LibraryMusicOptions(AudioFitOptions):
    folder: str = Field(
        default="",
        title="Music folder",
        description="Folder of CC0 tracks. Empty means <data dir>/assets/music.",
    )


def default_music_folder(data_dir: Path) -> Path:
    return data_dir / "assets" / "music"


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
        if self.options.folder:
            return Path(self.options.folder)
        return default_music_folder(self.context.data_dir)

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
        ensure_parent(output)
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
