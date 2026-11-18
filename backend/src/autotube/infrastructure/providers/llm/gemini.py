from __future__ import annotations

from typing import Any

from pydantic import Field

from autotube.domain.capabilities import Capability, TextRequest
from autotube.infrastructure.providers.context import ProviderContext
from autotube.infrastructure.providers.http_retry import HttpOptions, post_provider_json
from autotube.infrastructure.providers.json_response import dig
from autotube.infrastructure.providers.llm.image_payload import image_base64, image_mime_type
from autotube.infrastructure.providers.spec import ProviderSpec
from autotube.shared.errors import UpstreamFailure

SECRET = "gemini_api_key"


class GeminiOptions(HttpOptions):
    model: str = Field(
        default="gemini-2.5-flash",
        min_length=1,
        title="Model",
        description="Gemini model id available on the free tier.",
    )
    base_url: str = Field(
        min_length=1,
        default="https://generativelanguage.googleapis.com/v1beta",
        title="Base URL",
        description="Generative Language API root.",
    )


def user_parts(request: TextRequest) -> list[dict[str, Any]]:
    parts: list[dict[str, Any]] = [{"text": request.prompt}]
    for image in request.images:
        inline = {"mime_type": image_mime_type(image), "data": image_base64(image)}
        parts.append({"inline_data": inline})
    return parts


def generation_config(request: TextRequest) -> dict[str, Any]:
    config: dict[str, Any] = {
        "maxOutputTokens": request.max_tokens,
        "temperature": request.temperature,
    }
    if request.json_schema is not None:
        config["responseMimeType"] = "application/json"
        config["responseJsonSchema"] = request.json_schema
    return config


def gemini_payload(request: TextRequest) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "contents": [{"role": "user", "parts": user_parts(request)}],
        "generationConfig": generation_config(request),
    }
    if request.system:
        payload["systemInstruction"] = {"parts": [{"text": request.system}]}
    return payload


def candidate_text(body: dict[str, Any]) -> str:
    parts = dig(body, "Gemini", "candidates", 0, "content", "parts")
    text = "".join(str(part.get("text", "")) for part in parts if isinstance(part, dict))
    if not text:
        raise UpstreamFailure("Gemini returned no text")
    return text


class GeminiText:
    provider_id = "gemini"

    def __init__(self, options: GeminiOptions, context: ProviderContext) -> None:
        self.options = options
        self.context = context

    def available(self) -> str | None:
        return self.context.missing_secret(SECRET, "Gemini API key")

    def generate(self, request: TextRequest) -> str:
        body = post_provider_json(
            self.context,
            self.options,
            self.options.base_url,
            f"models/{self.options.model}:generateContent",
            gemini_payload(request),
            {"x-goog-api-key": self.context.secret(SECRET)},
            "Gemini",
        )
        return candidate_text(body)


SPEC = ProviderSpec(
    provider_id=GeminiText.provider_id,
    capability=Capability.LLM,
    name="Google Gemini",
    description="Gemini through the Generative Language API free tier. Accepts image input.",
    options=GeminiOptions,
    factory=GeminiText,
    offline=False,
    required_secrets=(SECRET,),
)
