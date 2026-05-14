"""Step definitions for tests/features/workout_analysis.feature."""
from __future__ import annotations

import json
from datetime import date
from pathlib import Path
from unittest.mock import patch

import pytest
import yaml
from pytest_bdd import given, when, then, parsers, scenarios

from fitlog.analysis.workouts import (
    frequency_by_body_area,
    workout_streak,
    personal_records,
    incomplete_session_rate,
)

scenarios("../features/workout_analysis.feature")


# ---------------------------------------------------------------------------
# Shared state fixture
# ---------------------------------------------------------------------------

@pytest.fixture
def ctx(vault_path):
    """Mutable context dict shared across steps within a scenario."""
    return {
        "vault_path": vault_path,
        "result": None,
        "today_mock": None,
    }


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _write_workout_entry(vault_path: Path, entry: dict) -> None:
    entry_date = date.fromisoformat(entry["date"])
    log_file = vault_path / "logs" / "workouts" / f"{entry_date.year}.jsonl"
    log_file.parent.mkdir(parents=True, exist_ok=True)
    with log_file.open("a") as f:
        f.write(json.dumps(entry) + "\n")


def _call_fn(ctx, fn, **kwargs):
    today_str = ctx.get("today_mock")
    if today_str:
        fake_today = date.fromisoformat(today_str)
        with patch("fitlog.data.log.date") as mock_date_cls:
            mock_date_cls.today.return_value = fake_today
            mock_date_cls.fromisoformat.side_effect = date.fromisoformat
            ctx["result"] = fn(ctx["vault_path"], **kwargs)
    else:
        ctx["result"] = fn(ctx["vault_path"], **kwargs)


def _exercise_yaml_dir(vault_path: Path) -> Path:
    d = vault_path / "exercises"
    d.mkdir(parents=True, exist_ok=True)
    return d


# ---------------------------------------------------------------------------
# Given steps
# ---------------------------------------------------------------------------

@given("a temporary vault directory")
def given_temp_vault(ctx):
    pass  # vault_path fixture provides the tmp directory


@given(parsers.parse('today is mocked to "{date_str}"'))
def given_today_mocked(ctx, date_str):
    ctx["today_mock"] = date_str


@given(parsers.parse('an exercise YAML "{ex_id}" with primary body areas "{areas}"'))
def given_exercise_yaml_with_areas(ctx, ex_id, areas):
    area_list = [a.strip() for a in areas.split(",")]
    yaml_dir = _exercise_yaml_dir(ctx["vault_path"])
    data = {
        "id": ex_id,
        "name": ex_id,
        "body_areas": {
            "primary": area_list,
        },
    }
    with (yaml_dir / f"{ex_id}.yaml").open("w") as f:
        yaml.dump(data, f)


@given(parsers.parse('an exercise YAML "{ex_id}" with no body areas'))
def given_exercise_yaml_no_areas(ctx, ex_id):
    yaml_dir = _exercise_yaml_dir(ctx["vault_path"])
    data = {
        "id": ex_id,
        "name": ex_id,
    }
    with (yaml_dir / f"{ex_id}.yaml").open("w") as f:
        yaml.dump(data, f)


@given(parsers.parse('a workout entry on "{d}" with exercise "{ex_id}" and {n:d} sets'))
def given_workout_entry(ctx, d, ex_id, n):
    sets = [{"reps": 10}] * n
    entry = {
        "id": f"wo-{d.replace('-', '')}",
        "date": d,
        "exercises": [
            {"exercise_id": ex_id, "sets": sets}
        ],
    }
    _write_workout_entry(ctx["vault_path"], entry)


@given(parsers.parse('a weighted workout on "{d}" for exercise "{ex_id}" with weight {weight:d} reps {reps:d}'))
def given_weighted_workout(ctx, d, ex_id, weight, reps):
    entry = {
        "id": f"wo-{d.replace('-', '')}",
        "date": d,
        "exercises": [
            {"exercise_id": ex_id, "sets": [{"weight": weight, "reps": reps}]}
        ],
    }
    _write_workout_entry(ctx["vault_path"], entry)


@given(parsers.parse('a bodyweight workout on "{d}" for exercise "{ex_id}" with reps {reps:d}'))
def given_bodyweight_workout(ctx, d, ex_id, reps):
    entry = {
        "id": f"wo-{d.replace('-', '')}",
        "date": d,
        "exercises": [
            {"exercise_id": ex_id, "sets": [{"reps": reps}]}
        ],
    }
    _write_workout_entry(ctx["vault_path"], entry)


# ---------------------------------------------------------------------------
# When steps
# ---------------------------------------------------------------------------

@when("I call frequency_by_body_area")
def when_frequency_by_body_area(ctx):
    yaml_dir = _exercise_yaml_dir(ctx["vault_path"])
    _call_fn(ctx, frequency_by_body_area, exercise_yaml_dir=yaml_dir)


@when(parsers.parse('I call frequency_by_body_area with start_date "{start}" and end_date "{end}"'))
def when_frequency_by_body_area_range(ctx, start, end):
    yaml_dir = _exercise_yaml_dir(ctx["vault_path"])
    _call_fn(ctx, frequency_by_body_area, exercise_yaml_dir=yaml_dir, start_date=start, end_date=end)


@when("I call workout_streak")
def when_workout_streak(ctx):
    _call_fn(ctx, workout_streak)


@when(parsers.parse('I call workout_streak with start_date "{start}" and end_date "{end}"'))
def when_workout_streak_range(ctx, start, end):
    _call_fn(ctx, workout_streak, start_date=start, end_date=end)


@when(parsers.parse('I call personal_records for exercise "{ex_id}"'))
def when_personal_records(ctx, ex_id):
    _call_fn(ctx, personal_records, exercise_id=ex_id)


@when("I call incomplete_session_rate")
def when_incomplete_session_rate(ctx):
    _call_fn(ctx, incomplete_session_rate)


# ---------------------------------------------------------------------------
# Then steps
# ---------------------------------------------------------------------------

@then(parsers.parse('the body area "{area}" count equals {value:d}'))
def then_body_area_count(ctx, area, value):
    actual = ctx["result"]["body_areas"].get(area)
    assert actual == value, f"Expected body_areas[{area!r}]={value}, got {actual}"


@then("the body_areas dict is empty")
def then_body_areas_empty(ctx):
    actual = ctx["result"]["body_areas"]
    assert actual == {}, f"Expected empty body_areas, got {actual}"


@then(parsers.parse('the streak result field "{field}" equals {value:d}'))
def then_streak_field_int(ctx, field, value):
    actual = ctx["result"][field]
    assert actual == value, f"Expected {field}={value}, got {actual}"


@then(parsers.parse('the streak result field "{field}" equals "{value}"'))
def then_streak_field_str(ctx, field, value):
    actual = ctx["result"][field]
    assert actual == value, f"Expected {field}={value!r}, got {actual!r}"


@then(parsers.parse('the streak result field "{field}" is None'))
def then_streak_field_none(ctx, field):
    actual = ctx["result"][field]
    assert actual is None, f"Expected {field}=None, got {actual!r}"


@then(parsers.parse('the pr result field "{field}" equals string "{value}"'))
def then_pr_field_str(ctx, field, value):
    actual = ctx["result"][field]
    assert actual == value, f"Expected {field}={value!r}, got {actual!r}"


@then(parsers.parse('the pr result field "{field}" equals float {value:g}'))
def then_pr_field_float(ctx, field, value):
    actual = ctx["result"][field]
    assert actual == pytest.approx(value, rel=1e-3), f"Expected {field}={value}, got {actual}"


@then(parsers.parse('the pr result field "{field}" equals int {value:d}'))
def then_pr_field_int(ctx, field, value):
    actual = ctx["result"][field]
    assert actual == value, f"Expected {field}={value}, got {actual}"


@then(parsers.parse('the pr result field "{field}" is None'))
def then_pr_field_none(ctx, field):
    actual = ctx["result"][field]
    assert actual is None, f"Expected {field}=None, got {actual!r}"


@then(parsers.parse('the incomplete result field "{field}" equals int {value:d}'))
def then_incomplete_field_int(ctx, field, value):
    actual = ctx["result"][field]
    assert actual == value, f"Expected {field}={value}, got {actual}"


@then(parsers.parse('the incomplete result field "{field}" equals float {value:g}'))
def then_incomplete_field_float(ctx, field, value):
    actual = ctx["result"][field]
    assert actual == pytest.approx(value, rel=1e-3), f"Expected {field}={value}, got {actual}"
