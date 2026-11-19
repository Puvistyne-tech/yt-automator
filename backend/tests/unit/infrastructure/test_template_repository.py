from __future__ import annotations

from datetime import timedelta

import pytest
from sqlalchemy import inspect

from autotube.domain.pipeline_templates import TemplateStatus
from autotube.domain.ports import TemplateRepository
from autotube.infrastructure.db.database import Database
from autotube.infrastructure.db.tables import PipelineTemplateRow
from autotube.infrastructure.db.template_repository import SqlTemplateRepository
from autotube.shared.errors import RuleConflict
from tests.fixtures.fake_repositories import InMemoryTemplates
from tests.fixtures.fake_runtime import START
from tests.fixtures.template_records import template


@pytest.fixture(params=["sql", "fake"])
def templates(request: pytest.FixtureRequest, database: Database) -> TemplateRepository:
    if request.param == "sql":
        return SqlTemplateRepository(database)
    return InMemoryTemplates()


def test_added_templates_round_trip_and_are_found_by_type_id(
    templates: TemplateRepository,
) -> None:
    stored = template(definition={"brief": "facts", "topics": ["space"]})
    templates.add(stored)
    assert templates.get("tpl-1") == stored
    assert templates.find_by_type_id("t_tpl-1") == stored
    assert templates.find_by_type_id("t_missing") is None
    assert templates.get("missing") is None


def test_update_replaces_the_stored_template(templates: TemplateRepository) -> None:
    templates.add(template())
    changed = template(name="Renamed", revision=2, status=TemplateStatus.DRAFT)
    templates.update(changed)
    assert templates.get("tpl-1") == changed
    assert templates.list() == [changed]


def test_list_orders_by_creation_and_delete_is_idempotent(templates: TemplateRepository) -> None:
    later = template("b", created_at=START + timedelta(days=1))
    templates.add(later)
    templates.add(template("a"))
    assert [item.id for item in templates.list()] == ["a", "b"]
    templates.delete("a")
    templates.delete("a")
    assert templates.list() == [later]


def test_adding_a_stored_type_id_is_refused(templates: TemplateRepository) -> None:
    templates.add(template("a"))
    with pytest.raises(RuleConflict) as raised:
        templates.add(template("b", type_id="t_a"))
    assert raised.value.code == "template_type_taken"
    assert [item.id for item in templates.list()] == ["a"]


def test_adding_a_stored_id_is_refused(templates: TemplateRepository) -> None:
    templates.add(template("a"))
    with pytest.raises(RuleConflict) as raised:
        templates.add(template("a", type_id="t_other"))
    assert raised.value.code == "template_exists"
    assert templates.list() == [template("a")]


def test_update_cannot_take_another_templates_type_id(templates: TemplateRepository) -> None:
    templates.add(template("a"))
    templates.add(template("b"))
    with pytest.raises(RuleConflict) as raised:
        templates.update(template("b", type_id="t_a"))
    assert raised.value.code == "template_type_taken"
    assert templates.get("b") == template("b")


def test_rows_that_no_longer_decode_are_skipped(database: Database) -> None:
    templates = SqlTemplateRepository(database)
    broken = template("broken").model_dump(mode="json") | {"audience": "teens"}
    row = PipelineTemplateRow(
        id="broken", type_id="t_broken", status="ready", created_at="0", payload=broken
    )
    with database.immediate_session() as session:
        session.add(row)
    templates.add(template())
    assert templates.list() == [template()]
    assert templates.find_by_type_id("t_broken") is None


def test_migration_creates_the_templates_table(database: Database) -> None:
    schema = inspect(database.engine)
    columns = {column["name"] for column in schema.get_columns("pipeline_templates")}
    indexes = {index["name"] for index in schema.get_indexes("pipeline_templates")}
    assert columns == {"id", "type_id", "status", "created_at", "payload"}
    assert {"ix_pipeline_templates_status", "ix_pipeline_templates_created_at"} <= indexes
