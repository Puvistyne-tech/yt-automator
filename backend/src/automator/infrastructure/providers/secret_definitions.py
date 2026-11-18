from __future__ import annotations

from automator.domain.secrets import SecretDefinition

PROVIDER_SECRETS: tuple[SecretDefinition, ...] = (
    SecretDefinition(
        name="groq_api_key",
        title="Groq API key",
        description="Free key from console.groq.com for the Groq text provider.",
    ),
    SecretDefinition(
        name="gemini_api_key",
        title="Gemini API key",
        description="Free key from aistudio.google.com for the Gemini text provider.",
    ),
    SecretDefinition(
        name="huggingface_token",
        title="Hugging Face token",
        description="Read token for gated model downloads such as FLUX.1-dev in mflux.",
    ),
)
