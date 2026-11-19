from __future__ import annotations

from collections.abc import Callable
from functools import partial

from autotube.pipelines.narrated_video.story.model import Story
from tests.fixtures.kids_fakes import FakeWriter
from tests.fixtures.list_data import list_story, list_writer
from tests.fixtures.quiz_data import quiz_story, quiz_writer

SCRIPTED_WRITERS: dict[str, Callable[[], FakeWriter]] = {
    "list": list_writer,
    "countdown": partial(list_writer, countdown=True),
    "quiz": quiz_writer,
}
SCRIPTED_STORIES: dict[str, Callable[[], Story]] = {
    "list": list_story,
    "countdown": partial(list_story, countdown=True),
    "quiz": quiz_story,
}
