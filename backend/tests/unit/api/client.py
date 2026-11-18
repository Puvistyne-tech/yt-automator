from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any
from urllib.parse import parse_qs, urlparse

from fastapi.testclient import TestClient
from httpx2 import Response

from automator.main import Runtime

WAIT_SECONDS = 10.0
POLL_SECONDS = 0.02


def ok(response: Response, status: int = 200) -> Any:
    assert response.status_code == status, response.text
    return response.json() if response.content else None


def send(client: TestClient, method: str, path: str, body: Any = None) -> Response:
    return client.request(method.upper(), path, json=body)


def error_of(response: Response, status: int) -> dict[str, Any]:
    assert response.status_code == status, response.text
    body: dict[str, Any] = response.json()["error"]
    assert set(body) == {"code", "message", "fields"}
    return body


def automation_body(channel_id: str, **overrides: Any) -> dict[str, Any]:
    body: dict[str, Any] = {
        "name": "Bedtime",
        "pipeline_type": "fake",
        "settings": {"topic": "owls"},
        "languages": ["en"],
        "targets": [{"channel_id": channel_id, "language": "en", "variants": ["landscape"]}],
    }
    return body | overrides


@dataclass
class Api:
    client: TestClient
    runtime: Runtime

    def credential(self, **overrides: Any) -> dict[str, Any]:
        body = {"name": "Project", "client_id": "cid", "client_secret": "csecret"} | overrides
        created: dict[str, Any] = ok(self.client.post("/api/credentials", json=body), 201)
        return created

    def connect(self, credential_id: str) -> str:
        started = ok(
            self.client.post("/api/channels/connect", json={"credential_id": credential_id})
        )
        state = parse_qs(urlparse(started["authorization_url"]).query)["state"][0]
        response = self.client.get("/api/oauth/callback", params={"code": "c0de", "state": state})
        assert response.status_code == 303, response.text
        location = urlparse(response.headers["location"])
        assert location.path == "/channels"
        return parse_qs(location.query)["connected"][0]

    def channel(self) -> str:
        return self.connect(self.credential()["id"])

    def automation(self, channel_id: str, **overrides: Any) -> dict[str, Any]:
        body = automation_body(channel_id, **overrides)
        created: dict[str, Any] = ok(self.client.post("/api/automations", json=body), 201)
        return created

    def start(self, automation_id: str) -> dict[str, Any]:
        started: dict[str, Any] = ok(
            self.client.post(f"/api/automations/{automation_id}/runs"), 201
        )
        return started

    def wait_for(self, run_id: str, *statuses: str) -> dict[str, Any]:
        deadline = time.monotonic() + WAIT_SECONDS
        while time.monotonic() < deadline:
            run: dict[str, Any] = ok(self.client.get(f"/api/runs/{run_id}"))
            if run["status"] in statuses:
                return run
            time.sleep(POLL_SECONDS)
        raise AssertionError(f"run {run_id} never reached {statuses}")

    def finished_run(self, **overrides: Any) -> dict[str, Any]:
        automation = self.automation(self.channel(), **overrides)
        run = self.start(automation["id"])
        return self.wait_for(run["id"], "awaiting_review", "approved", "failed")

    def approved_run(self) -> dict[str, Any]:
        run = self.finished_run()
        body = {"decision": "approved"}
        approved: dict[str, Any] = ok(self.client.post(f"/api/runs/{run['id']}/review", json=body))
        return approved
