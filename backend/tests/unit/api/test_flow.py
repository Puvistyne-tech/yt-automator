from __future__ import annotations

from automator.domain.credentials import credential_secret_name
from tests.fixtures.fake_runtime import InMemorySecrets
from tests.fixtures.fake_youtube import FakeYouTube
from tests.unit.api.client import Api, ok


def test_end_to_end_from_credential_to_published_upload(
    api: Api, youtube: FakeYouTube, secrets: InMemorySecrets
) -> None:
    client = api.client
    credential = api.credential(daily_quota_units=5000)
    assert secrets.get(credential_secret_name(credential["id"])) == "csecret"
    channel_id = api.connect(credential["id"])
    assert ok(client.get("/api/channels"))[0]["youtube_channel_id"] == "UC-fake"
    automation = api.automation(channel_id)
    run = api.start(automation["id"])
    assert run["status"] == "queued"
    run = api.wait_for(run["id"], "awaiting_review")
    assert run["score"] == 90.0
    video = next(item for item in run["artifacts"] if item["kind"] == "video")
    response = client.get(
        f"/api/runs/{run['id']}/artifacts/{video['id']}", headers={"Range": "bytes=1-2"}
    )
    assert response.status_code == 206
    assert response.content == b"wl"
    assert response.headers["content-type"].startswith("video/mp4")
    assert response.headers["content-range"] == "bytes 1-2/4"
    ok(client.post(f"/api/runs/{run['id']}/review", json={"decision": "approved", "notes": "ok"}))
    published = ok(client.post(f"/api/runs/{run['id']}/publish"))
    assert published["status"] == "published"
    assert [upload["status"] for upload in published["uploads"]] == ["done"]
    assert youtube.uploads[0].title == "Story in en"
    [listed] = ok(client.get("/api/credentials"))
    assert listed["quota_used_today"] == published["uploads"][0]["quota_units"] > 0
    assert listed["has_secret"] is True
    dashboard = ok(client.get("/api/dashboard"))
    assert dashboard["automations"] == dashboard["enabled_automations"] == 1
    assert (dashboard["channels"], dashboard["runs_today"]) == (1, 1)
    assert dashboard["runs_awaiting_review"] == 0
    assert dashboard["recent_runs"][0]["status"] == "published"
    assert dashboard["recent_runs"][0]["automation_name"] == "Bedtime"
    assert dashboard["quota"] == [
        {
            "credential_id": credential["id"],
            "name": "Project",
            "used": listed["quota_used_today"],
            "limit": 5000,
        }
    ]
    assert ok(client.get(f"/api/automations/{automation['id']}"))["last_run"]["id"] == run["id"]
