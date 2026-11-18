from __future__ import annotations

from typing import Any

import httpx
from pydantic import Field

from autotube.domain.capabilities import Capability, TextRequest
from autotube.infrastructure.providers.context import ProviderContext
from autotube.infrastructure.providers.http_retry import HttpOptions, post_provider_json
from autotube.infrastructure.providers.json_response import dig
from autotube.infrastructure.providers.llm.image_payload import image_base64
from autotube.infrastructure.providers.spec import ProviderSpec


class OllamaOptions(HttpOptions):
    model: str = Field(
        default="gemma3:12b",
        min_length=1,
        title="Model",
        description="A pulled Ollama model. Use a vision model (gemma3, qwen2.5vl) for images.",
    )
    base_url: str = Field(
        min_length=1,
        default="http://127.0.0.1:11434",
        title="Server URL",
        description="Where the local Ollama server listens.",
    )
    probe_timeout_seconds: float = Field(
        default=1.0,
        gt=0,
        title="Probe timeout",
        description="Seconds to wait when checking that the server is running.",
    )


def user_message(request: TextRequest) -> dict[str, Any]:
    message: dict[str, Any] = {"role": "user", "content": request.prompt}
    if request.images:
        message["images"] = [image_base64(image) for image in request.images]
    return message


def ollama_payload(request: TextRequest, model: str) -> dict[str, Any]:
    messages = [{"role": "system", "content": request.system}] if request.system else []
    messages.append(user_message(request))
    payload: dict[str, Any] = {
        "model": model,
        "messages": messages,
        "stream": False,
        "options": {"temperature": request.temperature, "num_predict": request.max_tokens},
    }
    if request.json_schema is not None:
        payload["format"] = request.json_schema
    return payload


def model_pulled(model: str, tags: Any) -> bool:
    names = {str(entry.get("name", "")) for entry in tags if isinstance(entry, dict)}
    return model in names or f"{model}:latest" in names


class OllamaText:
    provider_id = "ollama"

    def __init__(self, options: OllamaOptions, context: ProviderContext) -> None:
        self.options = options
        self.context = context

    def available(self) -> str | None:
        url = self.options.base_url.rstrip("/")
        try:
            with self.context.http(self.options.probe_timeout_seconds) as client:
                tags = client.get(f"{url}/api/tags").json().get("models", [])
        except (httpx.HTTPError, ValueError, AttributeError):
            return f"Ollama is not running at {url} (start it with `ollama serve`)"
        if not model_pulled(self.options.model, tags):
            return f"Ollama model {self.options.model!r} is not pulled (ollama pull it)"
        return None

    def generate(self, request: TextRequest) -> str:
        body = post_provider_json(
            self.context,
            self.options,
            self.options.base_url,
            "api/chat",
            ollama_payload(request, self.options.model),
            {},
            "Ollama",
        )
        return str(dig(body, "Ollama", "message", "content"))


SPEC = ProviderSpec(
    provider_id=OllamaText.provider_id,
    capability=Capability.LLM,
    name="Ollama (local)",
    description="Any model served by a local Ollama. Accepts image input with vision models.",
    options=OllamaOptions,
    factory=OllamaText,
    offline=True,
)
