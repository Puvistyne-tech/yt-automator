from __future__ import annotations

from autotube.pipelines.narrated_video.settings.root import KidsStorySettings
from autotube.pipelines.narrated_video.story.model import StoryDraft, StoryText, labels_of
from autotube.pipelines.narrated_video.structures.length import scene_range
from autotube.pipelines.narrated_video.structures.registry import spec_of
from autotube.pipelines.narrated_video.structures.spec import Schema

MORAL = "moral"
SCENES = "scenes"
SCENE = "StoryScene"
LABELS = "SceneLabels"
REQUIRED = "required"
PROPERTIES = "properties"


def with_required(names: list[str], added: list[str]) -> list[str]:
    return [*names, *(name for name in added if name not in names)]


def with_fields(schema: Schema, fields: Schema, required: bool) -> Schema:
    names = with_required(schema.get(REQUIRED, []), list(fields)) if required else None
    changed = {**schema, PROPERTIES: {**schema[PROPERTIES], **fields}}
    return changed if names is None else {**changed, REQUIRED: names}


def with_text_field(schema: Schema, name: str) -> Schema:
    title = schema[PROPERTIES][name].get("title", name)
    return with_fields(schema, {name: {"type": "string", "minLength": 1, "title": title}}, True)


def counted(array: Schema, low: int, high: int) -> Schema:
    return {**array, "minItems": low, "maxItems": high}


def shaped_scenes(schema: Schema, shapes: list[Schema]) -> Schema:
    base = schema["$defs"][SCENE]
    items = [with_fields(base, shape, True) for shape in shapes]
    return counted({"type": "array", "prefixItems": items}, len(items), len(items))


def scenes_schema(schema: Schema, settings: KidsStorySettings) -> Schema:
    shapes = spec_of(settings).scene_shapes
    if shapes is not None:
        return shaped_scenes(schema, shapes(settings))
    return counted(schema[PROPERTIES][SCENES], *scene_range(settings))


def with_moral(schema: Schema, settings: KidsStorySettings) -> Schema:
    return with_text_field(schema, MORAL) if spec_of(settings).moral_required(settings) else schema


def draft_schema(settings: KidsStorySettings) -> Schema:
    schema = with_moral(StoryDraft.model_json_schema(), settings)
    return with_fields(schema, {SCENES: scenes_schema(schema, settings)}, True)


def labels_schema(count: int) -> Schema:
    return counted({"type": "array", "items": {"$ref": f"#/$defs/{LABELS}"}}, count, count)


def text_schema(settings: KidsStorySettings, story: StoryDraft) -> Schema:
    schema = with_moral(StoryText.model_json_schema(), settings)
    count = len(story.scenes)
    narrations = counted(schema[PROPERTIES]["narrations"], count, count)
    schema = with_fields(schema, {"narrations": narrations}, True)
    if labels_of(story) is None:
        return schema
    return with_fields(schema, {"scene_labels": labels_schema(count)}, True)
