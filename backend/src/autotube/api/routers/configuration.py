from __future__ import annotations

from fastapi import APIRouter

from autotube.api.container import App
from autotube.api.schemas.requests import SecretValueRequest, SettingsRequest
from autotube.api.schemas.responses import ERROR_RESPONSES, NO_CONTENT_RESPONSE
from autotube.domain.providers import ProviderConfig, ProvidersView
from autotube.domain.secrets import SecretStatus
from autotube.domain.settings import AppSettings

router = APIRouter(tags=["configuration"], responses=ERROR_RESPONSES)


@router.get("/providers", summary="Provider descriptors and the configured chains")
def get_providers(app: App) -> ProvidersView:
    return app.config.get_providers.execute()


@router.put("/providers", summary="Replace the provider chains")
def save_providers(body: list[ProviderConfig], app: App) -> list[ProviderConfig]:
    return app.config.save_providers.execute(body)


@router.get("/secrets", summary="Known secrets and whether each is set")
def list_secrets(app: App) -> list[SecretStatus]:
    return app.config.list_secrets.execute()


@router.put(
    "/secrets/{name:path}",
    **NO_CONTENT_RESPONSE,
    summary="Store a secret in the keychain",
)
def set_secret(name: str, body: SecretValueRequest, app: App) -> None:
    app.config.set_secret.execute(name, body.value)


@router.delete(
    "/secrets/{name:path}",
    **NO_CONTENT_RESPONSE,
    summary="Remove a secret from the keychain",
)
def delete_secret(name: str, app: App) -> None:
    app.config.delete_secret.execute(name)


@router.get("/settings", summary="Application settings")
def get_settings(app: App) -> AppSettings:
    return app.config.get_settings.execute()


@router.put("/settings", summary="Change application settings; data_dir is read-only")
def save_settings(body: SettingsRequest, app: App) -> AppSettings:
    return app.config.save_settings.execute(body.sent_fields())
