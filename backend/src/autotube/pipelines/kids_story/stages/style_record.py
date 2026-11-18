from __future__ import annotations

from autotube.domain.pipeline import NewArtifact, StageContext
from autotube.domain.run_enums import ArtifactKind
from autotube.pipelines.kids_story.artifacts import Role, artifact, folder, write_json
from autotube.pipelines.kids_story.settings.root import KidsStorySettings
from autotube.pipelines.kids_story.stages.media_types import JSON
from autotube.pipelines.kids_story.styles.resolve import ResolvedStyle, resolve_style


def style_summary(style: ResolvedStyle) -> str:
    held = style.motion.held_frame_rate
    frames = f", held frames at {held} per second" if held else ""
    return (
        f"visual style: {style.title} ({style.style_id}); palette {', '.join(style.palette)}; "
        f"outline {style.outline.value}, texture {style.texture.value}{frames}"
    )


def recorded_style(context: StageContext, settings: KidsStorySettings) -> NewArtifact:
    style = resolve_style(settings)
    context.log(style_summary(style))
    path = folder(context, "art") / "style.json"
    write_json(path, style.model_dump(mode="json"))
    return artifact(
        ArtifactKind.TEXT, path, JSON, Role.STYLE, style_id=style.style_id, title=style.title
    )
