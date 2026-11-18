from __future__ import annotations

from pydantic import BaseModel, ConfigDict, JsonValue

JsonObject = dict[str, JsonValue]


class DomainModel(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
