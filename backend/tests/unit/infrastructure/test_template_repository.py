from __future__ import annotations

from datetime import timedelta

import pytest
from sqlalchemy import inspect
from sqlalchemy.exc import IntegrityError

from autotube.domain.pipeline_templates import TemplateStatus
from autotube.domain.ports import TemplateRepository
from autotube.infrastructure.db.database import Database
from autotube.infrastructure.db.template_repository import SqlTemplateRepository
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
    first = template("a")
    second = template("b", created_at=START + timedelta(days=1))
    templates.add(first)
    templates.add(second)
    assert [item.id for item in templates.list()] == ["a", "b"]
    templates.delete("a")
    templates.delete("a")
    assert templates.list() == [second]


def test_stored_type_ids_are_unique(database: Database) -> None:
    templates = SqlTemplateRepository(database)
    templates.add(template("a"))
    with pytest.raises(IntegrityError):
        templates.add(template("b", type_id="t_a"))


def test_adding_an_existing_id_is_refused(database: Database) -> None:
    templates = SqlTemplateRepository(database)
    templates.add(template("a"))
    with pytest.raises(IntegrityError):
        templates.add(template("a", type_id="t_other"))


def test_migration_creates_the_templates_table(database: Database) -> None:
    schema = inspect(database.engine)
    columns = {column["name"] for column in schema.get_columns("pipeline_templates")}
    indexes = {index["name"] for index in schema.get_indexes("pipeline_templates")}
    assert columns == {"id", "type_id", "status", "created_at", "payload"}
    assert {"ix_pipeline_templates_status", "ix_pipeline_templates_created_at"} <= indexes
