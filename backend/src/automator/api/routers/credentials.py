from __future__ import annotations

from fastapi import APIRouter

from automator.api.container import App
from automator.api.schemas.responses import CREATED, ERROR_RESPONSES, NO_CONTENT_RESPONSE
from automator.domain.credentials import CredentialInput, CredentialPatch, CredentialView

router = APIRouter(prefix="/credentials", tags=["credentials"], responses=ERROR_RESPONSES)


@router.get("", summary="List credentials with secret presence and today's quota use")
def list_credentials(app: App) -> list[CredentialView]:
    return app.channels.list_credentials.execute()


@router.post("", status_code=CREATED, summary="Add a Google API credential")
def create_credential(body: CredentialInput, app: App) -> CredentialView:
    return app.channels.create_credential.execute(body)


@router.patch("/{credential_id}", summary="Change a credential")
def update_credential(credential_id: str, body: CredentialPatch, app: App) -> CredentialView:
    return app.channels.update_credential.execute(credential_id, body)


@router.delete(
    "/{credential_id}", summary="Delete a credential that no channel uses", **NO_CONTENT_RESPONSE
)
def delete_credential(credential_id: str, app: App) -> None:
    app.channels.delete_credential.execute(credential_id)
