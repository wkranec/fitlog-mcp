"""BDD step definitions for server.feature."""
from __future__ import annotations

import json
from pathlib import Path

import pytest
from pytest_bdd import given, parsers, scenarios, then, when
from fastapi.testclient import TestClient

from fitlog.server import app, get_vault_path

scenarios("../features/server.feature")


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def ctx(vault_path):
    app.dependency_overrides[get_vault_path] = lambda: vault_path
    client = TestClient(app)
    yield {"client": client, "vault_path": vault_path, "response": None}
    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Given
# ---------------------------------------------------------------------------

@given("a fresh vault")
def fresh_vault(ctx):
    pass


@given(parsers.parse('an exercise "{exercise_id}" with name "{name}" and load_type "{load_type}" exists'))
def exercise_exists(ctx, exercise_id, name, load_type):
    vault_path: Path = ctx["vault_path"]
    exercises_dir = vault_path / "exercises"
    exercises_dir.mkdir(parents=True, exist_ok=True)
    yaml_file = exercises_dir / f"{exercise_id}.yaml"
    yaml_file.write_text(f"{exercise_id}:\n  name: {name}\n  load_type: {load_type}\n")


# ---------------------------------------------------------------------------
# When
# ---------------------------------------------------------------------------

@when(parsers.parse('I GET "{path}"'))
def do_get(ctx, path):
    ctx["response"] = ctx["client"].get(path)


@when(parsers.parse('I log weight {value:g} "{unit}" on date "{date}"'))
def log_weight(ctx, value, unit, date):
    body = {"date": date, "weight": {"value": value, "unit": unit}}
    ctx["response"] = ctx["client"].post(
        "/v1/metrics/log",
        content=json.dumps(body),
        headers={"Content-Type": "application/json"},
    )


@when(parsers.parse('I POST metrics with only date "{date}"'))
def log_metrics_date_only(ctx, date):
    body = {"date": date}
    ctx["response"] = ctx["client"].post(
        "/v1/metrics/log",
        content=json.dumps(body),
        headers={"Content-Type": "application/json"},
    )


@when(parsers.parse('I create exercise "{exercise_id}" named "{name}" with load_type "{load_type}"'))
def create_exercise_step(ctx, exercise_id, name, load_type):
    body = {"exercise_id": exercise_id, "name": name, "load_type": load_type}
    ctx["response"] = ctx["client"].post(
        "/v1/workouts/create-exercise",
        content=json.dumps(body),
        headers={"Content-Type": "application/json"},
    )


@when(parsers.parse('I log exercise "{exercise_id}" on date "{date}" with {count:d} bodyweight set of {reps:d} reps'))
def log_exercise_bodyweight(ctx, exercise_id, date, count, reps):
    sets = [{"reps": reps}] * count
    body = {"date": date, "exercise_id": exercise_id, "sets": sets}
    ctx["response"] = ctx["client"].post(
        "/v1/workouts/log-exercise",
        content=json.dumps(body),
        headers={"Content-Type": "application/json"},
    )


# ---------------------------------------------------------------------------
# Then
# ---------------------------------------------------------------------------

@then(parsers.parse("the response status is {status:d}"))
def check_status(ctx, status):
    assert ctx["response"].status_code == status, (
        f"Expected {status}, got {ctx['response'].status_code}: {ctx['response'].text}"
    )


@then("the response status is 400 or 422")
def check_status_400_or_422(ctx):
    assert ctx["response"].status_code in (400, 422), (
        f"Expected 400 or 422, got {ctx['response'].status_code}: {ctx['response'].text}"
    )


@then(parsers.parse('the response JSON has "{key}" equal to "{value}"'))
def check_json_key_string(ctx, key, value):
    data = ctx["response"].json()
    assert str(data[key]) == value, f"Expected {key}={value!r}, got {data[key]!r}"


@then(parsers.parse('the response JSON has "{key}" equal to {value:d}'))
def check_json_key_int(ctx, key, value):
    data = ctx["response"].json()
    assert data[key] == value, f"Expected {key}={value}, got {data[key]}"


@then(parsers.parse('the response JSON "{key}" contains "{item}"'))
def check_json_list_contains(ctx, key, item):
    data = ctx["response"].json()
    assert item in data[key], f"Expected {item!r} in {data[key]}"
