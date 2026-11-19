from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class NarratedDefinition(BaseModel):
    model_config = ConfigDict(extra="forbid", title="Narrated video template")
