"""Step definitions for tests/features/goals.feature."""
from __future__ import annotations

import json
from datetime import date
from pathlib import Path
from unittest.mock import patch

import pytest
import yaml as yaml_module
from pytest_bdd import given, when, then, parsers, scenarios

from fitlog.analysis.goals import check_goal_status, get_goal_history, list_goals

scenarios("../features/goals.feature")


# ---------------------------------------------------------------------------
# Shared state fixture
# ---------------------------------------------------------------------------

@pytest.fixture
def ctx(vault_path):
    """Mutable context dict shared across steps within a scenario."""
    return {
        "vault_path": vault_path,
        "result": None,
        "error": None,
        "today_mock": None,
    }


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _write_metrics_entry(vault_path: Path, entry: dict) -> None:
    entry_date = date.fromisoformat(entry["date"])
    log_file = vault_path / "logs" / "metrics" / f"{entry_date.year}.jsonl"
    log_file.parent.mkdir(parents=True, exist_ok=True)
    with log_file.open("a") as f:
        f.write(json.dumps(entry) + "\n")


def _write_workout_entry(vault_path: Path, entry: dict) -> None:
    entry_date = date.fromisoformat(entry["date"])
    log_file = vault_path / "logs" / "workouts" / f"{entry_date.year}.jsonl"
    log_file.parent.mkdir(parents=True, exist_ok=True)
    with log_file.open("a") as f:
        f.write(json.dumps(entry) + "\n")


def _call_fn(ctx, fn, **kwargs):
    today_str = ctx.get("today_mock")
    try:
        if today_str:
            fake_today = date.fromisoformat(today_str)
            with patch("fitlog.data.log.date") as mock_date_cls, \
                 patch("fitlog.analysis.goals._today") as mock_today:
                mock_date_cls.today.return_value = fake_today
                mock_date_cls.fromisoformat.side_effect = date.fromisoformat
                mock_today.return_value = fake_today
                ctx["result"] = fn(ctx["vault_path"], **kwargs)
        else:
            ctx["result"] = fn(ctx["vault_path"], **kwargs)
    except Exception as exc:
        ctx["error"] = exc


# ---------------------------------------------------------------------------
# Given steps
# ---------------------------------------------------------------------------

@given("a temporary vault directory")
def given_temp_vault(ctx):
    pass  # vault_path fixture provides the tmp directory


@given(parsers.parse('today is mocked to "{date_str}"'))
def given_today_mocked(ctx, date_str):
    ctx["today_mock"] = date_str


@given("a goals.yaml with content:")
def given_goals_yaml(ctx, docstring):
    goals_file = ctx["vault_path"] / "goals.yaml"
    goals_file.write_text(docstring)


@given(parsers.parse('a metrics entry with date "{d}" and sleep duration {duration:g} no quality'))
def given_sleep_entry_no_quality(ctx, d, duration):
    _write_metrics_entry(ctx["vault_path"], {"date": d, "sleep": {"duration_hours": duration}})


@given(parsers.parse('a timed workout on "{d}" for exercise "{ex_id}" with duration {duration:d} seconds'))
def given_timed_workout(ctx, d, ex_id, duration):
    entry = {
        "id": f"wo-{d.replace('-', '')}-{ex_id}",
        "date": d,
        "exercises": [
            {
                "exercise_id": ex_id,
                "sets": [{"duration_seconds": float(duration)}],
            }
        ],
    }
    _write_workout_entry(ctx["vault_path"], entry)


@given(parsers.parse('a workout entry on "{d}" with exercise "{ex_id}" and {n:d} sets'))
def given_workout_entry(ctx, d, ex_id, n):
    sets = [{"reps": 10}] * n
    entry = {
        "id": f"wo-{d.replace('-', '')}-{ex_id}",
        "date": d,
        "exercises": [
            {"exercise_id": ex_id, "sets": sets}
        ],
    }
    _write_workout_entry(ctx["vault_path"], entry)


# ---------------------------------------------------------------------------
# When steps
# ---------------------------------------------------------------------------

@when("I call list_goals")
def when_list_goals(ctx):
    _call_fn(ctx, list_goals)


@when(parsers.parse('I call check_goal_status for goal "{goal_id}"'))
def when_check_goal_status(ctx, goal_id):
    _call_fn(ctx, check_goal_status, goal_id=goal_id, as_of_date=ctx.get("today_mock"))


@when(parsers.parse('I call check_goal_status for goal "{goal_id}" expecting error'))
def when_check_goal_status_expecting_error(ctx, goal_id):
    _call_fn(ctx, check_goal_status, goal_id=goal_id, as_of_date=ctx.get("today_mock"))


@when(parsers.parse('I call get_goal_history for goal "{goal_id}" with days {days:d}'))
def when_get_goal_history_days(ctx, goal_id, days):
    _call_fn(ctx, get_goal_history, goal_id=goal_id, days=days)


@when(parsers.parse('I call get_goal_history for goal "{goal_id}" with start_date "{start}" and end_date "{end}"'))
def when_get_goal_history_range(ctx, goal_id, start, end):
    _call_fn(ctx, get_goal_history, goal_id=goal_id, start_date=start, end_date=end)


# ---------------------------------------------------------------------------
# Then steps — list_goals
# ---------------------------------------------------------------------------

@then(parsers.parse('the goals list has {count:d} entries'))
def then_goals_list_count(ctx, count):
    assert ctx["error"] is None, f"Unexpected error: {ctx['error']}"
    actual = ctx["result"]["goals"]
    assert len(actual) == count, f"Expected {count} goals, got {len(actual)}: {actual}"


@then(parsers.parse('the goals list contains goal_id "{goal_id}" with type "{gtype}"'))
def then_goals_list_contains(ctx, goal_id, gtype):
    goals = ctx["result"]["goals"]
    match = next((g for g in goals if g["goal_id"] == goal_id), None)
    assert match is not None, f"goal_id {goal_id!r} not found in {goals}"
    assert match["type"] == gtype, f"Expected type={gtype!r}, got {match['type']!r}"


# ---------------------------------------------------------------------------
# Then steps — check_goal_status
# ---------------------------------------------------------------------------

@then(parsers.parse('the status field "{field}" is True'))
def then_status_field_true(ctx, field):
    assert ctx["error"] is None, f"Unexpected error: {ctx['error']}"
    actual = ctx["result"][field]
    assert actual is True, f"Expected {field}=True, got {actual!r}"


@then(parsers.parse('the status field "{field}" is False'))
def then_status_field_false(ctx, field):
    assert ctx["error"] is None, f"Unexpected error: {ctx['error']}"
    actual = ctx["result"][field]
    assert actual is False, f"Expected {field}=False, got {actual!r}"


@then(parsers.parse('the status field "{field}" is None'))
def then_status_field_none(ctx, field):
    assert ctx["error"] is None, f"Unexpected error: {ctx['error']}"
    actual = ctx["result"][field]
    assert actual is None, f"Expected {field}=None, got {actual!r}"


@then(parsers.parse('the status field "{field}" equals float {value:g}'))
def then_status_field_float(ctx, field, value):
    assert ctx["error"] is None, f"Unexpected error: {ctx['error']}"
    actual = ctx["result"][field]
    assert actual == pytest.approx(value, rel=1e-3), f"Expected {field}={value}, got {actual}"


@then(parsers.parse('the status field "{field}" equals int {value:d}'))
def then_status_field_int(ctx, field, value):
    assert ctx["error"] is None, f"Unexpected error: {ctx['error']}"
    actual = ctx["result"][field]
    assert actual == value, f"Expected {field}={value}, got {actual}"


@then(parsers.parse('the status field "{field}" equals "{value}"'))
def then_status_field_str(ctx, field, value):
    assert ctx["error"] is None, f"Unexpected error: {ctx['error']}"
    actual = ctx["result"][field]
    assert actual == value, f"Expected {field}={value!r}, got {actual!r}"


@then(parsers.parse('the status pct_met_last_30_days is approximately {value:g}'))
def then_status_pct_met(ctx, value):
    assert ctx["error"] is None, f"Unexpected error: {ctx['error']}"
    actual = ctx["result"]["pct_met_last_30_days"]
    assert actual == pytest.approx(value, abs=0.01), f"Expected pct_met_last_30_days~{value}, got {actual}"


# ---------------------------------------------------------------------------
# Then steps — error cases
# ---------------------------------------------------------------------------

@then("a KeyError is raised")
def then_key_error_raised(ctx):
    assert ctx["error"] is not None, "Expected a KeyError but none was raised"
    assert isinstance(ctx["error"], KeyError), f"Expected KeyError, got {type(ctx['error'])}"


# ---------------------------------------------------------------------------
# Then steps — get_goal_history
# ---------------------------------------------------------------------------

@then(parsers.parse('the history has {count:d} entries'))
def then_history_count(ctx, count):
    assert ctx["error"] is None, f"Unexpected error: {ctx['error']}"
    actual = ctx["result"]["history"]
    assert len(actual) == count, f"Expected {count} history entries, got {len(actual)}: {actual}"


@then(parsers.parse('the history entry {idx:d} has date "{d}" and met True'))
def then_history_entry_met_true(ctx, idx, d):
    entry = ctx["result"]["history"][idx]
    assert entry["date"] == d, f"Expected date={d!r}, got {entry['date']!r}"
    assert entry["met"] is True, f"Expected met=True, got {entry['met']!r}"


@then(parsers.parse('the history entry {idx:d} has date "{d}" and met False'))
def then_history_entry_met_false(ctx, idx, d):
    entry = ctx["result"]["history"][idx]
    assert entry["date"] == d, f"Expected date={d!r}, got {entry['date']!r}"
    assert entry["met"] is False, f"Expected met=False, got {entry['met']!r}"


@then(parsers.parse('the frequency history contains a complete period "{period_key}" with met True'))
def then_frequency_history_period_met(ctx, period_key):
    assert ctx["error"] is None, f"Unexpected error: {ctx['error']}"
    history = ctx["result"]["history"]
    match = next((p for p in history if p["period"] == period_key), None)
    assert match is not None, f"Period {period_key!r} not found in history: {history}"
    assert match["complete"] is True, f"Expected period {period_key!r} to be complete"
    assert match["met"] is True, f"Expected period {period_key!r} to be met"
