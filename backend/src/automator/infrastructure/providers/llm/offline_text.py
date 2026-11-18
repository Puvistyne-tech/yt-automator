from __future__ import annotations

import json

from pydantic import Field

from automator.domain.capabilities import Capability, TextRequest
from automator.infrastructure.providers.context import ProviderContext
from automator.infrastructure.providers.llm.json_sample import sample_document
from automator.infrastructure.providers.spec import ProviderOptions, ProviderSpec


class OfflineTextOptions(ProviderOptions):
    template: str = Field(
        default="Offline draft. {topic}",
        title="Text template",
        description="Reply to plain text requests. {topic} becomes the start of the prompt.",
    )
    topic_words: int = Field(
        default=12,
        ge=1,
        title="Topic words",
        description="How many leading prompt words make up the topic.",
    )
    array_items: int = Field(
        default=3,
        ge=1,
        title="List length",
        description="Items generated for JSON arrays without a minimum length.",
    )


def topic_of(prompt: str, words: int) -> str:
    return " ".join(prompt.split()[:words]).rstrip(".,;:")


class OfflineText:
    provider_id = "offline_text"

    def __init__(self, options: OfflineTextOptions, context: ProviderContext) -> None:
        self.options = options
        self.context = context

    def available(self) -> str | None:
        return None

    def generate(self, request: TextRequest) -> str:
        topic = topic_of(request.prompt, self.options.topic_words)
        if request.json_schema is None:
            return self.options.template.replace("{topic}", topic)
        document = sample_document(request.json_schema, topic, self.options.array_items)
        return json.dumps(document, ensure_ascii=False)


SPEC = ProviderSpec(
    provider_id=OfflineText.provider_id,
    capability=Capability.LLM,
    name="Offline text",
    description="Deterministic placeholder text and schema-valid JSON. Always available.",
    options=OfflineTextOptions,
    factory=OfflineText,
    offline=True,
)
