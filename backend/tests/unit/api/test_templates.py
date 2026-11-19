from __future__ import annotations

from collections.abc import Iterator
from typing import Any

import pytest

from autotube.infrastructure.config import RuntimeConfig
from autotube.infrastructure.db.tables import PipelineTemplateRow
from autotube.main import Overrides, Runtime
from tests.fixtures.fake_engines import BUILTIN_TYPE, REFUSED_BRIEF, FakeEngineCatalog
from tests.fixtures.template_records import template
from tests.unit.api.client import Api, automation_body, error_of, ok, wired

TEMPLATE_BODY: dict[str, Any] = {
    "engine": "sample",
    "name": "Space facts",
    "audience": "general",
    "status": "ready",
    "definition": {"brief": "planets"},
}


@pytest.fixture
def served(config: RuntimeConfig, overrides: Overrides) -> Iterator[Api]:
    with wired(config, overrides, pipelines=None, engines=FakeEngineCatalog()) as client:
        runtime: Runtime = client.app.state.runtime  # type: ignore[attr-defined]
        yield Api(client, runtime)


def created(api: Api, **changes: Any) -> dict[str, Any]:
    made: dict[str, Any] = ok(api.client.post("/api/templates", json=TEMPLATE_BODY | changes), 201)
    return made


def automation_on(api: Api, type_id: str, name: str) -> None:
    api.automation(api.channel(), name=name, pipeline_type=type_id, settings={})


def test_engines_route_lists_definition_forms(served: Api) -> None:
    [engine] = ok(served.client.get("/api/template-engines"))
    assert set(engine) == {
        "engine_id",
        "name",
        "definition_schema",
        "definition_ui_schema",
        "blank",
    }
    assert engine["blank"] == {
        "kids": {"brief": "for a kids audience"},
        "general": {"brief": "for a general audience"},
    }
    assert set(engine["definition_schema"]["properties"]) == {"brief", "length"}


def test_create_list_and_get(served: Api) -> None:
    made = created(served, name=" Space facts ")
    assert (made["type_id"], made["name"], made["revision"]) == (
        f"t_{made['id']}",
        "Space facts",
        1,
    )
    listed = ok(served.client.get("/api/templates"))
    assert [(t["id"], t["builtin"], t["automations_using"]) for t in listed] == [
        (BUILTIN_TYPE, True, 0),
        (made["id"], False, 0),
    ]
    assert ok(served.client.get(f"/api/templates/{made['id']}")) == made
    assert ok(served.client.get(f"/api/templates/{BUILTIN_TYPE}"))["origin"] == "builtin"
    assert error_of(served.client.get("/api/templates/missing"), 404)["code"] == (
        "template_not_found"
    )


@pytest.mark.parametrize(
    ("changes", "fields"),
    [
        ({"name": " ", "origin": "builtin"}, ["name", "origin"]),
        ({"definition": {"brief": REFUSED_BRIEF}}, ["definition.brief"]),
        ({"type_id": "t_mine"}, ["type_id"]),
    ],
    ids=["name-and-origin", "engine-problem", "type-id"],
)
def test_create_reports_field_errors(
    served: Api, changes: dict[str, Any], fields: list[str]
) -> None:
    response = served.client.post("/api/templates", json=TEMPLATE_BODY | changes)
    assert sorted(error_of(response, 400)["fields"]) == fields


def test_a_stored_row_that_no_longer_decodes_is_hidden_but_deletable(served: Api) -> None:
    broken = template("broken").model_dump(mode="json") | {"audience": "teens"}
    row = PipelineTemplateRow(
        id="broken", type_id="t_broken", status="ready", created_at="0", payload=broken
    )
    with served.runtime.database.immediate_session() as session:
        session.add(row)
    assert error_of(served.client.get("/api/templates/broken"), 404)["code"] == (
        "template_not_found"
    )
    assert [t["id"] for t in ok(served.client.get("/api/templates"))] == [BUILTIN_TYPE]
    assert ok(served.client.delete("/api/templates/broken"), 204) is None
    assert error_of(served.client.delete("/api/templates/broken"), 404)["code"] == (
        "template_not_found"
    )


def test_update_revises_and_refuses_builtins_and_fixed_fields(served: Api) -> None:
    path = f"/api/templates/{created(served)['id']}"
    updated = ok(served.client.put(path, json=TEMPLATE_BODY | {"name": "Moon facts"}))
    assert (updated["name"], updated["revision"]) == ("Moon facts", 2)
    builtin = served.client.put(f"/api/templates/{BUILTIN_TYPE}", json=TEMPLATE_BODY)
    assert error_of(builtin, 409)["code"] == "template_builtin"
    for change, field in (({"audience": "kids"}, "audience"), ({"type_id": "t_x"}, "type_id")):
        refused = served.client.put(path, json=TEMPLATE_BODY | change)
        assert list(error_of(refused, 400)["fields"]) == [field]


def test_a_template_in_use_stays_ready_and_cannot_be_deleted(served: Api) -> None:
    made = created(served)
    path = f"/api/templates/{made['id']}"
    automation_on(served, made["type_id"], "Comets")
    assert ok(served.client.get(path))["automations_using"] == 1
    drafted = served.client.put(path, json=TEMPLATE_BODY | {"status": "draft"})
    assert error_of(drafted, 409)["code"] == "template_in_use"
    assert error_of(served.client.delete(path), 409)["code"] == "template_in_use"
    builtin = served.client.delete(f"/api/templates/{BUILTIN_TYPE}")
    assert error_of(builtin, 409)["code"] == "template_builtin"


def test_delete_removes_an_unused_template(served: Api) -> None:
    path = f"/api/templates/{created(served)['id']}"
    assert ok(served.client.delete(path), 204) is None
    assert error_of(served.client.get(path), 404)["code"] == "template_not_found"


def test_duplicate_with_and_without_a_body(served: Api) -> None:
    plain = ok(served.client.post(f"/api/templates/{BUILTIN_TYPE}/duplicate"), 201)
    assert (plain["name"], plain["status"], plain["origin"]) == (
        "Sample (copy)",
        "draft",
        "duplicate",
    )
    body = {"name": "Kids sample", "audience": "kids"}
    chosen = ok(served.client.post(f"/api/templates/{plain['id']}/duplicate", json=body), 201)
    assert (chosen["name"], chosen["audience"]) == ("Kids sample", "kids")
    missing = served.client.post("/api/templates/missing/duplicate")
    assert error_of(missing, 404)["code"] == "template_not_found"
    bad = served.client.post(f"/api/templates/{BUILTIN_TYPE}/duplicate", json={"audience": "teens"})
    assert list(error_of(bad, 400)["fields"]) == ["audience"]


def narrated_automation(api: Api, type_id: str) -> Any:
    channel_id = api.channel()
    targets = [{"channel_id": channel_id, "language": "en", "variants": ["episode"]}]
    body = automation_body(channel_id, pipeline_type=type_id, settings={}, targets=targets)
    return api.client.post("/api/automations", json=body)


def test_a_narrated_template_becomes_a_pipeline_type_once_ready(
    config: RuntimeConfig, overrides: Overrides
) -> None:
    with wired(config, overrides, pipelines=None) as client:
        api = Api(client, client.app.state.runtime)  # type: ignore[attr-defined]
        body = TEMPLATE_BODY | {"engine": "narrated_video", "audience": "kids", "definition": {}}
        made = created(api, **body | {"status": "draft"})
        type_id = made["type_id"]
        assert type_id not in [d["type_id"] for d in ok(client.get("/api/pipelines"))]
        assert error_of(narrated_automation(api, type_id), 400)["fields"]
        ok(client.put(f"/api/templates/{made['id']}", json=body))
        assert type_id in [d["type_id"] for d in ok(client.get("/api/pipelines"))]
        assert ok(narrated_automation(api, type_id), 201)["pipeline_type"] == type_id
