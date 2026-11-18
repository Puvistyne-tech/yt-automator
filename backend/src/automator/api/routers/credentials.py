from __future__ import annotations

from fastapi import APIRouter, Response, status

from automator.api.container import App, UseCases
from automator.api.schemas.responses import ERROR_RESPONSES
from automator.domain.credentials import (
    Credential,
    CredentialInput,
    CredentialPatch,
    CredentialView,
)

router = APIRouter(prefix="/credentials", tags=["credentials"], responses=ERROR_RESPONSES)


@router.get("", summary="List credentials with secret presence and today's quota use")
def list_credentials(app: App) -> list[CredentialView]:
    return app.channels.list_credentials.execute()


def listed(app: UseCases, credential: Credential) -> CredentialView:
    rows = app.channels.list_credentials.execute()
    return next(row for row in rows if row.id == credential.id)


@router.post("", status_code=status.HTTP_201_CREATED, summary="Add a Google API credential")
def create_credential(body: CredentialInput, app: App) -> CredentialView:
    return listed(app, app.channels.create_credential.execute(body))


@router.patch("/{credential_id}", summary="Change a credential")
def update_credential(credential_id: str, body: CredentialPatch, app: App) -> CredentialView:
    return listed(app, app.channels.update_credential.execute(credential_id, body))


@router.delete(
    "/{credential_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
    summary="Delete a credential that no channel uses",
)
def delete_credential(credential_id: str, app: App) -> None:
    app.channels.delete_credential.execute(credential_id)
