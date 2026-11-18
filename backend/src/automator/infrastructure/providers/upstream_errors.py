from __future__ import annotations

from collections.abc import Callable

from pydantic import ValidationError

from automator.shared.errors import UpstreamFailure, describe_error


def provider_output_failure(provider: str, error: OSError | ValidationError) -> UpstreamFailure:
    if isinstance(error, ValidationError):
        return UpstreamFailure(f"{provider} returned unusable output: {error.errors()[0]['msg']}")
    return UpstreamFailure(f"{provider} could not use its files: {describe_error(error)}")


def as_upstream[T](provider: str, operation: Callable[[], T]) -> T:
    try:
        return operation()
    except (OSError, ValidationError) as error:
        raise provider_output_failure(provider, error) from error
