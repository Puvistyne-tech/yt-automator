from __future__ import annotations

from automator.domain.capabilities import SpeechRequest
from automator.shared.errors import UpstreamFailure


def require_text(provider: str, request: SpeechRequest) -> str:
    if not request.text.strip():
        raise UpstreamFailure(f"{provider} needs some text to speak", "text_missing")
    return request.text
