"""Step definitions for tests/features/log.feature."""
from __future__ import annotations

import json
from datetime import date, timedelta
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest
from pytest_bdd import given, when, then, parsers, scenarios

from fitlog.data.log import append_entry, read_merged, read_merged_list

scenarios("../features/log.feature")


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

def _write_entry(vault_path: Path, log_type: str, entry: dict) -> None:
    entry_date = date.fromisoformat(entry["date"])
    log_file = vault_path / "logs" / log_type / f"{entry_date.year}.jsonl"
    log_file.parent.mkdir(parents=True, exist_ok=True)
    with log_file.open("a") as f:
        f.write(json.dumps(entry) + "\n")


def _do_read_merged(ctx, log_type, **kwargs):
    today_str = ctx.get("today_mock")
    if today_str:
        fake_today = date.fromisoformat(today_str)
        with patch("fitlog.data.log.date") as mock_date_cls:
            mock_date_cls.today.return_value = fake_today
            mock_date_cls.fromisoformat.side_effect = date.fromisoformat
            ctx["result"] = read_merged(log_type, ctx["vault_path"], **kwargs)
    else:
        ctx["result"] = read_merged(log_type, ctx["vault_path"], **kwargs)


def _do_read_merged_list(ctx, log_type, **kwargs):
    today_str = ctx.get("today_mock")
    if today_str:
        fake_today = date.fromisoformat(today_str)
        with patch("fitlog.data.log.date") as mock_date_cls:
            mock_date_cls.today.return_value = fake_today
            mock_date_cls.fromisoformat.side_effect = date.fromisoformat
            ctx["result"] = read_merged_list(log_type, ctx["vault_path"], **kwargs)
    else:
        ctx["result"] = read_merged_list(log_type, ctx["vault_path"], **kwargs)


# ---------------------------------------------------------------------------
# Given steps
# ---------------------------------------------------------------------------

@given("a temporary vault directory")
def given_temp_vault(ctx):
    pass  # vault_path fixture provides the tmp directory


@given(parsers.parse('today is mocked to "{date_str}"'))
def given_today_mocked(ctx, date_str):
    ctx["today_mock"] = date_str


# --- metrics log entry helpers ---

@given(parsers.parse('a metrics log entry date "{d}" weight {w:g}'))
def given_metrics_weight(ctx, d, w):
    _write_entry(ctx["vault_path"], "metrics", {"date": d, "weight_kg": w})


@given(parsers.parse('a metrics log entry date "{d}" weight {w:g} notes "{n}"'))
def given_metrics_weight_notes(ctx, d, w, n):
    _write_entry(ctx["vault_path"], "metrics", {"date": d, "weight_kg": w, "notes": n})


@given(parsers.parse('a metrics log entry date "{d}" tags "{tag}"'))
def given_metrics_tags(ctx, d, tag):
    _write_entry(ctx["vault_path"], "metrics", {"date": d, "tags": [tag]})


# --- workouts log entry helpers ---

@given(parsers.re(r'a workouts log entry date "(?P<d>[^"]+)" id "(?P<wid>[^"]+)" exercise "(?P<ex>[^"]+)" sets (?P<s>\d+)'))
def given_workouts_entry(ctx, d, wid, ex, s):
    _write_entry(ctx["vault_path"], "workouts", {"date": d, "id": wid, "exercise": ex, "sets": int(s)})


@given(parsers.re(r'a workouts log entry date "(?P<d>[^"]+)" id "(?P<wid>[^"]+)" sets (?P<s>\d+) notes "(?P<n>[^"]+)"'))
def given_workouts_entry_sets_notes(ctx, d, wid, s, n):
    _write_entry(ctx["vault_path"], "workouts", {"date": d, "id": wid, "sets": int(s), "notes": n})


@given(parsers.re(r'a workouts log entry date "(?P<d>[^"]+)" id "(?P<wid>[^"]+)" exercise "(?P<ex>[^"]+)" reps "(?P<reps_csv>[^"]+)"'))
def given_workouts_entry_reps(ctx, d, wid, ex, reps_csv):
    reps = [int(r.strip()) for r in reps_csv.split(",")]
    _write_entry(ctx["vault_path"], "workouts", {"date": d, "id": wid, "exercise": ex, "reps": reps})


@given(parsers.re(r'a workouts log entry date "(?P<d>[^"]+)" id "(?P<wid>[^"]+)" reps "(?P<reps_csv>[^"]+)"'))
def given_workouts_entry_reps_only(ctx, d, wid, reps_csv):
    reps = [int(r.strip()) for r in reps_csv.split(",")]
    _write_entry(ctx["vault_path"], "workouts", {"date": d, "id": wid, "reps": reps})


# ---------------------------------------------------------------------------
# When steps — append_entry
# ---------------------------------------------------------------------------

@when(parsers.parse('I append a metrics entry with date "{d}" and weight {w:g}'))
def when_append_metrics_weight(ctx, d, w):
    append_entry("metrics", {"date": d, "weight_kg": w}, ctx["vault_path"])


@when(parsers.parse('I append a workouts entry with date "{d}" id "{wid}" and exercise "{ex}"'))
def when_append_workouts(ctx, d, wid, ex):
    append_entry("workouts", {"date": d, "id": wid, "exercise": ex}, ctx["vault_path"])


# ---------------------------------------------------------------------------
# When steps — read_merged
# ---------------------------------------------------------------------------

@when(parsers.parse('I call read_merged for "{log_type}" with no filter'))
def when_read_merged_no_filter(ctx, log_type):
    _do_read_merged(ctx, log_type)


@when(parsers.parse('I call read_merged for "{log_type}" with days={days:d}'))
def when_read_merged_days(ctx, log_type, days):
    _do_read_merged(ctx, log_type, days=days)


@when(parsers.parse('I call read_merged for "{log_type}" with start_date "{s}" and end_date "{e}"'))
def when_read_merged_range(ctx, log_type, s, e):
    _do_read_merged(ctx, log_type, start_date=s, end_date=e)


@when(parsers.parse('I call read_merged for "{log_type}" with start_date "{s}" and no end_date'))
def when_read_merged_start_only(ctx, log_type, s):
    _do_read_merged(ctx, log_type, start_date=s)


@when(parsers.parse('I call read_merged for "{log_type}" with no start_date and end_date "{e}"'))
def when_read_merged_end_only(ctx, log_type, e):
    _do_read_merged(ctx, log_type, end_date=e)


@when(parsers.parse('I call read_merged for "{log_type}" with years {y1:d} and {y2:d}'))
def when_read_merged_years(ctx, log_type, y1, y2):
    _do_read_merged(ctx, log_type, years=[y1, y2])


# ---------------------------------------------------------------------------
# When steps — read_merged_list
# ---------------------------------------------------------------------------

@when(parsers.parse('I call read_merged_list for "{log_type}" with no filter'))
def when_read_merged_list_no_filter(ctx, log_type):
    _do_read_merged_list(ctx, log_type)


@when(parsers.parse('I call read_merged_list for "{log_type}" with start_date "{s}" and end_date "{e}"'))
def when_read_merged_list_range(ctx, log_type, s, e):
    _do_read_merged_list(ctx, log_type, start_date=s, end_date=e)


# ---------------------------------------------------------------------------
# Then steps — file system
# ---------------------------------------------------------------------------

@then(parsers.parse('the file "{rel_path}" exists in the vault'))
def then_file_exists(ctx, rel_path):
    full = ctx["vault_path"] / rel_path
    assert full.exists(), f"Expected {rel_path} to exist; vault contents: {list((ctx['vault_path']).rglob('*'))}"


@then(parsers.parse('the file "{rel_path}" contains {count:d} line'))
def then_file_lines_singular(ctx, rel_path, count):
    _assert_line_count(ctx, rel_path, count)


@then(parsers.parse('the file "{rel_path}" contains {count:d} lines'))
def then_file_lines(ctx, rel_path, count):
    _assert_line_count(ctx, rel_path, count)


def _assert_line_count(ctx, rel_path, count):
    lines = [l for l in (ctx["vault_path"] / rel_path).read_text().splitlines() if l.strip()]
    assert len(lines) == count, f"Expected {count} lines, got {len(lines)}"


@then(parsers.parse('line {n:d} of "{rel_path}" is valid JSON containing date "{d}"'))
def then_line_valid_json(ctx, n, rel_path, d):
    lines = [l for l in (ctx["vault_path"] / rel_path).read_text().splitlines() if l.strip()]
    obj = json.loads(lines[n - 1])
    assert obj["date"] == d


# ---------------------------------------------------------------------------
# Then steps — read_merged dict
# ---------------------------------------------------------------------------

@then(parsers.parse('the result contains key "{key}"'))
def then_result_contains_key(ctx, key):
    assert key in ctx["result"], f"Key '{key}' not found; keys={list(ctx['result'].keys())}"


@then(parsers.parse('the result does not contain key "{key}"'))
def then_result_no_key(ctx, key):
    assert key not in ctx["result"], f"Key '{key}' should not be in result"


@then(parsers.parse('result key "{dk}" field "{field}" equals float {value:g}'))
def then_result_field_float(ctx, dk, field, value):
    actual = ctx["result"][dk][field]
    assert actual == pytest.approx(value), f"Expected {value}, got {actual}"


@then(parsers.parse('result key "{dk}" field "{field}" equals string "{value}"'))
def then_result_field_string(ctx, dk, field, value):
    actual = ctx["result"][dk][field]
    assert actual == value, f"Expected '{value}', got '{actual}'"


@then(parsers.parse('result key "{dk}" field "{field}" equals int {value:d}'))
def then_result_field_int(ctx, dk, field, value):
    actual = ctx["result"][dk][field]
    assert actual == value, f"Expected {value}, got {actual}"


@then(parsers.parse('result key "{dk}" field "tags" is list {json_list}'))
def then_result_field_list(ctx, dk, json_list):
    expected = json.loads(json_list)
    actual = ctx["result"][dk]["tags"]
    assert actual == expected, f"Expected {expected}, got {actual}"


@then("the result is an empty dict")
def then_result_empty(ctx):
    assert ctx["result"] == {}, f"Expected empty dict, got {ctx['result']}"


# ---------------------------------------------------------------------------
# Then steps — workouts list in result dict
# ---------------------------------------------------------------------------

@then(parsers.parse('result key "{dk}" is a list with {count:d} item'))
def then_result_list_singular(ctx, dk, count):
    _assert_result_list(ctx, dk, count)


@then(parsers.parse('result key "{dk}" is a list with {count:d} items'))
def then_result_list_plural(ctx, dk, count):
    _assert_result_list(ctx, dk, count)


def _assert_result_list(ctx, dk, count):
    val = ctx["result"][dk]
    assert isinstance(val, list), f"Expected list, got {type(val)}"
    assert len(val) == count, f"Expected {count} items, got {len(val)}: {val}"


@then(parsers.parse('workout {idx:d} on "{dk}" field "{field}" equals string "{value}"'))
def then_workout_field_string(ctx, idx, dk, field, value):
    actual = ctx["result"][dk][idx][field]
    assert actual == value, f"Expected '{value}', got '{actual}'"


@then(parsers.parse('workout {idx:d} on "{dk}" field "{field}" equals int {value:d}'))
def then_workout_field_int(ctx, idx, dk, field, value):
    actual = ctx["result"][dk][idx][field]
    assert actual == value, f"Expected {value}, got {actual}"


@then(parsers.parse('workout {idx:d} on "{dk}" reps equals {json_list}'))
def then_workout_reps(ctx, idx, dk, json_list):
    expected = json.loads(json_list)
    actual = ctx["result"][dk][idx]["reps"]
    assert actual == expected, f"Expected {expected}, got {actual}"


# ---------------------------------------------------------------------------
# Then steps — read_merged_list
# ---------------------------------------------------------------------------

@then(parsers.parse('the list result has {count:d} items'))
def then_list_count(ctx, count):
    result = ctx["result"]
    assert isinstance(result, list), f"Expected list, got {type(result)}"
    assert len(result) == count, f"Expected {count} items, got {len(result)}: {result}"


@then(parsers.parse('the list result has {count:d} item'))
def then_list_count_singular(ctx, count):
    then_list_count(ctx, count)


@then(parsers.parse('list item {idx:d} has date "{d}"'))
def then_list_item_date(ctx, idx, d):
    item = ctx["result"][idx]
    assert item.get("date") == d, f"item[{idx}]['date'] expected '{d}', got '{item.get('date')}'"
