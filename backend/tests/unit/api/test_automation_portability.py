from __future__ import annotations

import json
from typing import Any

from tests.fixtures.fake_runtime import InMemorySecrets
from tests.unit.api.client import Api, error_of, ok


def export_of(api: Api) -> dict[str, Any]:
    automation = api.automation(api.channel())
    document: dict[str, Any] = ok(api.client.get(f"/api/automations/{automation['id']}/export"))
    return document


def import_body(document: dict[str, Any], **channel_map: str | None) -> dict[str, Any]:
    return {"document": document, "channel_map": channel_map}


def test_export_then_import_without_secrets(api: Api, secrets: InMemorySecrets) -> None:
    document = export_of(api)
    seeded = list(secrets.values.values())
    assert "csecret" in seeded and len(seeded) >= 2
    assert (document["app"], document["format_version"]) == ("AutoTube", 1)
    assert not [value for value in seeded if value in json.dumps(document)]
    preview = ok(api.client.post("/api/automations/import/preview", json=import_body(document)))
    assert preview["unknown_channels"] == []
    ok(api.client.post("/api/automations/import", json=import_body(document)), 201)
    assert len(ok(api.client.get("/api/automations"))) == 2


def test_export_unknown_automation_is_404(api: Api) -> None:
    error = error_of(api.client.get("/api/automations/missing/export"), 404)
    assert error["code"] == "automation_not_found"


def test_import_refuses_newer_format(api: Api) -> None:
    document = export_of(api) | {"format_version": 99}
    response = api.client.post("/api/automations/import/preview", json=import_body(document))
    error = error_of(response, 400)
    assert error["code"] == "validation_failed"
    assert "newer AutoTube (format 99)" in error["message"]
    assert set(error["fields"]) == {"format_version"}


def test_import_unknown_pipeline_and_channel(api: Api) -> None:
    document = export_of(api)
    document["automation"]["pipeline_type"] = "nope"
    document["automation"]["targets"][0]["channel_id"] = "gone"
    error = error_of(api.client.post("/api/automations/import", json=import_body(document)), 400)
    assert set(error["fields"]) == {"automation.pipeline_type", "channel_map.gone"}


def test_import_unknown_channel_preview_then_choice(api: Api) -> None:
    document = export_of(api)
    channel_id = document["automation"]["targets"][0]["channel_id"]
    document["automation"]["targets"][0]["channel_id"] = "gone"
    preview = ok(api.client.post("/api/automations/import/preview", json=import_body(document)))
    assert [item["id"] for item in preview["unknown_channels"]] == ["gone"]
    body = import_body(document, gone=channel_id)
    created = ok(api.client.post("/api/automations/import", json=body), 201)
    assert created["targets"][0]["channel_id"] == channel_id


def test_import_document_must_be_an_object(api: Api) -> None:
    response = api.client.post("/api/automations/import", json={"document": []})
    assert set(error_of(response, 400)["fields"]) == {"document"}
