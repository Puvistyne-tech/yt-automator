from __future__ import annotations

from fastapi import APIRouter, Response, status

from automator.api.container import App
from automator.api.schemas.requests import SecretValueRequest, SettingsRequest
from automator.api.schemas.responses import ERROR_RESPONSES
from automator.domain.providers import ProviderConfig, ProvidersView
from automator.domain.secrets import SecretStatus
from automator.domain.settings import AppSettings

router = APIRouter(tags=["configuration"], responses=ERROR_RESPONSES)
NO_CONTENT = status.HTTP_204_NO_CONTENT


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
    status_code=NO_CONTENT,
    response_class=Response,
    summary="Store a secret in the keychain",
)
def set_secret(name: str, body: SecretValueRequest, app: App) -> None:
    app.config.set_secret.execute(name, body.value)


@router.delete(
    "/secrets/{name:path}",
    status_code=NO_CONTENT,
    response_class=Response,
    summary="Remove a secret from the keychain",
)
def delete_secret(name: str, app: App) -> None:
    app.config.delete_secret.execute(name)


@router.get("/settings", summary="Application settings")
def get_settings(app: App) -> AppSettings:
    return app.config.get_settings.execute()


@router.put("/settings", summary="Change application settings; data_dir is read-only")
def save_settings(body: SettingsRequest, app: App) -> AppSettings:
    return app.config.save_settings.execute(body.changes())
