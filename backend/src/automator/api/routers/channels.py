from __future__ import annotations

from urllib.parse import urlencode

from fastapi import APIRouter, status
from fastapi.responses import RedirectResponse

from automator.api.container import App, Options
from automator.api.schemas.requests import ChannelPatchRequest, ConnectChannelRequest
from automator.api.schemas.responses import (
    ERROR_RESPONSES,
    NO_CONTENT_RESPONSE,
    ConnectChannelResponse,
)
from automator.domain.channels import Channel
from automator.domain.youtube import Playlist
from automator.shared.errors import AppError

router = APIRouter(tags=["channels"], responses=ERROR_RESPONSES)
CHANNELS_PAGE = "/channels"


@router.get("/channels", summary="List connected channels")
def list_channels(app: App) -> list[Channel]:
    return app.channels.list_channels.execute()


@router.post("/channels/connect", summary="Start connecting a channel through Google consent")
def connect_channel(body: ConnectChannelRequest, app: App) -> ConnectChannelResponse:
    started = app.channels.start_connect.execute(body.credential_id)
    return ConnectChannelResponse(authorization_url=started.authorization_url)


def channels_page(options_base: str, **query: str) -> RedirectResponse:
    target = f"{options_base.rstrip('/')}{CHANNELS_PAGE}?{urlencode(query)}"
    return RedirectResponse(target, status_code=status.HTTP_303_SEE_OTHER)


@router.get(
    "/oauth/callback",
    response_class=RedirectResponse,
    summary="Finish the Google consent and redirect to the channels page",
)
def oauth_callback(
    app: App, options: Options, code: str = "", state: str = "", error: str = ""
) -> RedirectResponse:
    if error:
        return channels_page(options.ui_base_url, error=error)
    if not code or not state:
        return channels_page(options.ui_base_url, error="missing_code")
    try:
        channel = app.channels.complete_connect.execute(code, state)
    except AppError as failure:
        return channels_page(options.ui_base_url, error=failure.code)
    return channels_page(options.ui_base_url, connected=channel.id)


@router.patch("/channels/{channel_id}", summary="Change a channel's upload defaults")
def update_channel(channel_id: str, body: ChannelPatchRequest, app: App) -> Channel:
    return app.channels.update_defaults.execute(channel_id, body.defaults)


@router.delete(
    "/channels/{channel_id}",
    **NO_CONTENT_RESPONSE,
    summary="Disconnect a channel that no enabled automation targets",
)
def delete_channel(channel_id: str, app: App) -> None:
    app.channels.delete_channel.execute(channel_id)


@router.get("/channels/{channel_id}/playlists", summary="List the channel's playlists")
def list_playlists(channel_id: str, app: App) -> list[Playlist]:
    return app.channels.list_playlists.execute(channel_id)
