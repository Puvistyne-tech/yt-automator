from __future__ import annotations

from collections.abc import Callable
from functools import partial

from tests.fixtures.kids_fakes import FakeWriter
from tests.fixtures.list_data import list_writer

SCRIPTED_WRITERS: dict[str, Callable[[], FakeWriter]] = {
    "list": list_writer,
    "countdown": partial(list_writer, countdown=True),
}
