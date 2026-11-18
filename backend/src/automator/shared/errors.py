from __future__ import annotations

from collections.abc import Mapping


class AppError(Exception):
    def __init__(self, code: str, message: str, fields: Mapping[str, str] | None = None) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.fields: dict[str, str] = dict(fields or {})


class NotFound(AppError):  # noqa: N818
    def __init__(self, entity: str, entity_id: str) -> None:
        super().__init__(f"{entity}_not_found", f"{entity} {entity_id!r} was not found")
        self.entity = entity
        self.entity_id = entity_id


class ValidationFailed(AppError):  # noqa: N818
    def __init__(self, fields: Mapping[str, str], message: str = "Validation failed") -> None:
        super().__init__("validation_failed", message, fields)


class RuleConflict(AppError):  # noqa: N818
    pass


class UpstreamFailure(AppError):  # noqa: N818
    def __init__(self, message: str, code: str = "upstream_failure") -> None:
        super().__init__(code, message)


def describe_error(error: Exception) -> str:
    return str(error) or type(error).__name__


def raise_if_invalid(errors: Mapping[str, str]) -> None:
    if errors:
        raise ValidationFailed(errors)
