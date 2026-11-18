from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel

from automator.shared.clock import to_utc

SORTABLE_FORMAT = "%Y-%m-%dT%H:%M:%S.%fZ"


def sortable_time(moment: datetime) -> str:
    return to_utc(moment).strftime(SORTABLE_FORMAT)


def to_payload(model: BaseModel) -> dict[str, Any]:
    return model.model_dump(mode="json")


def from_payload[M: BaseModel](model_type: type[M], payload: Any) -> M:
    return model_type.model_validate(payload)
