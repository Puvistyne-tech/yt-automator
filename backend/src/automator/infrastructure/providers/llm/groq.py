from __future__ import annotations

from typing import Any, Literal

from pydantic import Field

from automator.domain.capabilities import Capability, TextRequest
from automator.infrastructure.providers.context import ProviderContext
from automator.infrastructure.providers.http_retry import HttpOptions, post_provider_json
from automator.infrastructure.providers.json_response import dig
from automator.infrastructure.providers.llm.image_payload import reject_images
from automator.infrastructure.providers.spec import ProviderSpec

SECRET = "groq_api_key"


class GroqOptions(HttpOptions):
    model: str = Field(
        default="openai/gpt-oss-120b",
        min_length=1,
        title="Model",
        description="Groq model id, for example openai/gpt-oss-120b or llama-3.3-70b-versatile.",
    )
    base_url: str = Field(
        min_length=1,
        default="https://api.groq.com/openai/v1",
        title="Base URL",
        description="OpenAI-compatible API root.",
    )
    structured_output: Literal["json_schema", "json_object"] = Field(
        default="json_schema",
        title="Structured output",
        description="How a JSON schema request is enforced: strict schema or plain JSON mode.",
    )


def response_format(request: TextRequest, mode: str) -> dict[str, Any] | None:
    if request.json_schema is None:
        return None
    if mode == "json_object":
        return {"type": "json_object"}
    schema = {"name": "response", "schema": request.json_schema}
    return {"type": "json_schema", "json_schema": schema}


def chat_payload(request: TextRequest, options: GroqOptions) -> dict[str, Any]:
    messages = [{"role": "system", "content": request.system}] if request.system else []
    messages.append({"role": "user", "content": request.prompt})
    payload: dict[str, Any] = {
        "model": options.model,
        "messages": messages,
        "max_tokens": request.max_tokens,
        "temperature": request.temperature,
    }
    if (format_ := response_format(request, options.structured_output)) is not None:
        payload["response_format"] = format_
    return payload


class GroqText:
    provider_id = "groq"

    def __init__(self, options: GroqOptions, context: ProviderContext) -> None:
        self.options = options
        self.context = context

    def available(self) -> str | None:
        return self.context.missing_secret(SECRET, "Groq API key")

    def generate(self, request: TextRequest) -> str:
        reject_images(self.provider_id, request)
        body = post_provider_json(
            self.context,
            self.options,
            self.options.base_url,
            "chat/completions",
            chat_payload(request, self.options),
            {"Authorization": f"Bearer {self.context.secret(SECRET)}"},
            "Groq",
        )
        return str(dig(body, "Groq", "choices", 0, "message", "content"))


SPEC = ProviderSpec(
    provider_id=GroqText.provider_id,
    capability=Capability.LLM,
    name="Groq",
    description="Fast hosted open models on Groq's free tier. Text only, no image input.",
    options=GroqOptions,
    factory=GroqText,
    offline=False,
    required_secrets=(SECRET,),
)
