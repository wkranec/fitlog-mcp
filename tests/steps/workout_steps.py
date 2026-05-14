"""Step definitions for tests/features/workout_logging.feature."""
from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml
from pytest_bdd import given, when, then, parsers, scenarios

from fitlog.tools.workouts import log_exercise, create_exercise

scenarios("../features/workout_logging.feature")


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
    }


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _call_log_exercise(ctx, **kwargs):
    """Call log_exercise, capturing errors into ctx['error']."""
    try:
        ctx["result"] = log_exercise(ctx["vault_path"], **kwargs)
    except Exception as exc:  # noqa: BLE001
        ctx["error"] = exc


def _call_create_exercise(ctx, **kwargs):
    """Call create_exercise, capturing errors into ctx['error']."""
    try:
        ctx["result"] = create_exercise(ctx["vault_path"], **kwargs)
    except Exception as exc:  # noqa: BLE001
        ctx["error"] = exc


def _write_exercise_yaml(vault_path: Path, exercise_id: str, name: str, load_type: str) -> None:
    """Directly write an exercise YAML fixture to the vault (no create_exercise call)."""
    exercises_dir = vault_path / "exercises"
    exercises_dir.mkdir(parents=True, exist_ok=True)
    content = f"{exercise_id}:\n  name: {name}\n  load_type: {load_type}\n"
    (exercises_dir / f"{exercise_id}.yaml").write_text(content)


def _read_workout_entries(vault_path: Path, year: int = 2025) -> list[dict]:
    """Read all JSONL lines from the workout log for the given year."""
    path = vault_path / "logs" / "workouts" / f"{year}.jsonl"
    if not path.exists():
        return []
    entries = []
    for line in path.read_text().splitlines():
        line = line.strip()
        if line:
            entries.append(json.loads(line))
    return entries


# ---------------------------------------------------------------------------
# Given steps
# ---------------------------------------------------------------------------

@given("a temporary vault directory")
def given_temp_vault(ctx):
    pass  # vault_path fixture provides the tmp directory


@given(parsers.parse(
    'an exercise "{exercise_id}" with name "{name}" and load_type "{load_type}" exists in the vault'
))
def given_exercise_exists(ctx, exercise_id, name, load_type):
    _write_exercise_yaml(ctx["vault_path"], exercise_id, name, load_type)


# ---------------------------------------------------------------------------
# When steps — log_exercise
# ---------------------------------------------------------------------------

@when(parsers.parse(
    'I call log_exercise with date "{date}" exercise "{exercise_id}" and sets {sets_json}'
))
def when_log_exercise(ctx, date, exercise_id, sets_json):
    sets = json.loads(sets_json)
    _call_log_exercise(ctx, date=date, exercise_id=exercise_id, sets=sets)


@when(parsers.parse(
    'I call log_exercise with date "{date}" exercise "{exercise_id}" '
    'sets {sets_json} notes "{notes}" raw_input "{raw_input}"'
))
def when_log_exercise_with_notes(ctx, date, exercise_id, sets_json, notes, raw_input):
    sets = json.loads(sets_json)
    _call_log_exercise(
        ctx,
        date=date,
        exercise_id=exercise_id,
        sets=sets,
        notes=notes,
        raw_input=raw_input,
    )


# ---------------------------------------------------------------------------
# When steps — create_exercise
# ---------------------------------------------------------------------------

@when(parsers.parse(
    'I call create_exercise with id "{exercise_id}" name "{name}" load_type "{load_type}"'
))
def when_create_exercise(ctx, exercise_id, name, load_type):
    _call_create_exercise(ctx, exercise_id=exercise_id, name=name, load_type=load_type)


# ---------------------------------------------------------------------------
# Then steps — result assertions
# ---------------------------------------------------------------------------

@then(parsers.parse('the result status is "{status}"'))
def then_result_status(ctx, status):
    assert ctx["error"] is None, f"Unexpected error: {ctx['error']}"
    assert ctx["result"]["status"] == status


@then(parsers.parse('the result exercise_id is "{exercise_id}"'))
def then_result_exercise_id(ctx, exercise_id):
    assert ctx["result"]["exercise_id"] == exercise_id


@then(parsers.parse("the result sets_logged is {count:d}"))
def then_result_sets_logged(ctx, count):
    assert ctx["error"] is None, f"Unexpected error: {ctx['error']}"
    assert ctx["result"]["sets_logged"] == count


# ---------------------------------------------------------------------------
# Then steps — error assertions
# ---------------------------------------------------------------------------

@then("a workout error is raised")
def then_workout_error(ctx):
    assert ctx["error"] is not None, "Expected an error but none was raised"


@then(parsers.parse('the error message mentions "{text}"'))
def then_error_message_mentions(ctx, text):
    assert ctx["error"] is not None, "Expected an error but none was raised"
    assert text in str(ctx["error"]), (
        f"Expected error message to mention '{text}', got: {ctx['error']}"
    )


@then("no workout file is written")
def then_no_workout_file(ctx):
    log_dir = ctx["vault_path"] / "logs" / "workouts"
    if log_dir.exists():
        files = list(log_dir.glob("*.jsonl"))
        assert files == [], f"Expected no JSONL files, found: {files}"


# ---------------------------------------------------------------------------
# Then steps — file system
# ---------------------------------------------------------------------------

@then(parsers.parse('the file "{rel_path}" exists in the vault'))
def then_file_exists(ctx, rel_path):
    full = ctx["vault_path"] / rel_path
    assert full.exists(), f"Expected {rel_path} to exist"


@then(parsers.parse('the file "{rel_path}" contains {count:d} lines'))
def then_file_lines_plural(ctx, rel_path, count):
    _assert_line_count(ctx, rel_path, count)


@then(parsers.parse('the file "{rel_path}" contains {count:d} line'))
def then_file_lines_singular(ctx, rel_path, count):
    _assert_line_count(ctx, rel_path, count)


def _assert_line_count(ctx, rel_path, count):
    lines = [
        l for l in (ctx["vault_path"] / rel_path).read_text().splitlines() if l.strip()
    ]
    assert len(lines) == count, f"Expected {count} lines, got {len(lines)}"


# ---------------------------------------------------------------------------
# Then steps — JSONL content
# ---------------------------------------------------------------------------

@then(parsers.parse('the written workout entry has notes "{notes}" and raw_input "{raw_input}"'))
def then_entry_has_notes_and_raw_input(ctx, notes, raw_input):
    entries = _read_workout_entries(ctx["vault_path"])
    assert entries, "No workout entries found"
    entry = entries[-1]
    exercises = entry.get("exercises", [])
    assert exercises, "No exercises in entry"
    ex = exercises[0]
    assert ex.get("notes") == notes, f"Expected notes='{notes}', got '{ex.get('notes')}'"
    assert ex.get("raw_input") == raw_input, (
        f"Expected raw_input='{raw_input}', got '{ex.get('raw_input')}'"
    )


@then("the written workout entry has no null fields")
def then_no_null_fields(ctx):
    entries = _read_workout_entries(ctx["vault_path"])
    assert entries, "No workout entries found"
    for entry in entries:
        _check_no_nulls(entry)


def _check_no_nulls(obj):
    """Recursively assert no None values in a structure."""
    if isinstance(obj, dict):
        for key, val in obj.items():
            assert val is not None, f"Field '{key}' is null"
            _check_no_nulls(val)
    elif isinstance(obj, list):
        for item in obj:
            _check_no_nulls(item)


@then(parsers.parse('both written entries have the same workout id "{workout_id}"'))
def then_same_workout_id(ctx, workout_id):
    entries = _read_workout_entries(ctx["vault_path"])
    assert len(entries) == 2, f"Expected 2 entries, got {len(entries)}"
    ids = [e.get("id") for e in entries]
    assert ids[0] == workout_id, f"First entry id: '{ids[0]}' != '{workout_id}'"
    assert ids[1] == workout_id, f"Second entry id: '{ids[1]}' != '{workout_id}'"


# ---------------------------------------------------------------------------
# Then steps — create_exercise file assertions
# ---------------------------------------------------------------------------

@then(parsers.parse('the exercise file "{rel_path}" exists in the vault'))
def then_exercise_file_exists(ctx, rel_path):
    full = ctx["vault_path"] / rel_path
    assert full.exists(), f"Expected exercise file {rel_path} to exist"


@then(parsers.parse('the exercise file contains load_type "{load_type}"'))
def then_exercise_file_load_type(ctx, load_type):
    # Find the most recently created exercise yaml
    result = ctx["result"]
    assert result is not None, "No result from create_exercise"
    file_path = ctx["vault_path"] / result["file"]
    data = yaml.safe_load(file_path.read_text())
    exercise_id = result["exercise_id"]
    assert data[exercise_id]["load_type"] == load_type, (
        f"Expected load_type='{load_type}', got '{data[exercise_id]['load_type']}'"
    )
