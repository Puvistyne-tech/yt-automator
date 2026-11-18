from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi import FastAPI
from starlette.exceptions import HTTPException
from starlette.responses import Response
from starlette.staticfiles import StaticFiles

INDEX_FILE = "index.html"
API_SEGMENT = "api"


class SinglePageFiles(StaticFiles):
    async def get_response(self, path: str, scope: Any) -> Response:
        try:
            return await super().get_response(path, scope)
        except HTTPException as error:
            is_api = path.split("/", 1)[0] == API_SEGMENT
            if error.status_code != 404 or is_api:
                raise
            return await super().get_response(INDEX_FILE, scope)


def mount_web_ui(app: FastAPI, dist_dir: Path) -> bool:
    if not (dist_dir / INDEX_FILE).is_file():
        return False
    app.mount("/", SinglePageFiles(directory=dist_dir, html=True), name="web")
    return True
