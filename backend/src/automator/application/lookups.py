from __future__ import annotations

from automator.shared.errors import NotFound


def require[T](value: T | None, entity: str, entity_id: str) -> T:
    if value is None:
        raise NotFound(entity, entity_id)
    return value
