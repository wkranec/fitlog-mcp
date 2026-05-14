"""Step definitions for tests/features/metrics_logging.feature."""
from __future__ import annotations

import json
from pathlib import Path

import pytest
from pytest_bdd import given, when, then, parsers, scenarios

from fitlog.tools.metrics import log_metrics

scenarios("../features/metrics_logging.feature")


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

def _call_log_metrics(ctx, **kwargs):
    """Call log_metrics, capturing errors into ctx['error']."""
    try:
        ctx["result"] = log_metrics(ctx["vault_path"], **kwargs)
    except Exception as exc:  # noqa: BLE001
        ctx["error"] = exc


# ---------------------------------------------------------------------------
# Given steps
# ---------------------------------------------------------------------------

@given("a temporary vault directory")
def given_temp_vault(ctx):
    pass  # vault_path fixture provides the tmp directory


# ---------------------------------------------------------------------------
# When steps
# ---------------------------------------------------------------------------

@when(parsers.parse('I call log_metrics with date "{date}" and weight value {value:g} unit "{unit}"'))
def when_log_weight(ctx, date, value, unit):
    _call_log_metrics(ctx, date=date, weight={"value": value, "unit": unit})


@when(parsers.parse('I call log_metrics with date "{date}" weight {w:g} lbs and hrv {h:g} ms'))
def when_log_weight_and_hrv(ctx, date, w, h):
    _call_log_metrics(
        ctx,
        date=date,
        weight={"value": w, "unit": "lbs"},
        hrv={"value": h, "unit": "ms"},
    )


@when(parsers.parse('I call log_metrics with date "{date}" and invalid weight unit "{unit}"'))
def when_log_weight_invalid_unit(ctx, date, unit):
    _call_log_metrics(ctx, date=date, weight={"value": 180.0, "unit": unit})


@when(parsers.parse('I call log_metrics with date "{date}" and sleep quality {quality:d}'))
def when_log_sleep_bad_quality(ctx, date, quality):
    _call_log_metrics(ctx, date=date, sleep={"duration_hours": 7.0, "quality": quality})


@when(parsers.parse('I call log_metrics with only date "{date}"'))
def when_log_date_only(ctx, date):
    _call_log_metrics(ctx, date=date)


@when(parsers.parse('I call log_metrics with date "{date}" and sleep duration {duration:g}'))
def when_log_sleep_duration_only(ctx, date, duration):
    _call_log_metrics(ctx, date=date, sleep={"duration_hours": duration})


@when(parsers.parse('I call log_metrics with date "{date}" and sleep duration {duration:g} quality {quality:d} source "{source}"'))
def when_log_sleep_full(ctx, date, duration, quality, source):
    _call_log_metrics(
        ctx,
        date=date,
        sleep={"duration_hours": duration, "quality": quality, "source": source},
    )


@when(parsers.parse('I call log_metrics with date "{date}" and hrv value {value:g} source "{source}"'))
def when_log_hrv_with_source(ctx, date, value, source):
    _call_log_metrics(ctx, date=date, hrv={"value": value, "unit": "ms", "source": source})


@when(parsers.parse('I call log_metrics with date "{date}" and blood_pressure {systolic:d} over {diastolic:d}'))
def when_log_blood_pressure(ctx, date, systolic, diastolic):
    _call_log_metrics(
        ctx,
        date=date,
        blood_pressure={"systolic": systolic, "diastolic": diastolic, "unit": "mmHg"},
    )


@when(parsers.parse('I call log_metrics with date "{date}" and spo2 value {value:g}'))
def when_log_spo2(ctx, date, value):
    _call_log_metrics(ctx, date=date, spo2={"value": value, "unit": "%"})


# ---------------------------------------------------------------------------
# Then steps — result assertions
# ---------------------------------------------------------------------------

@then(parsers.parse('the result status is "{status}"'))
def then_result_status(ctx, status):
    assert ctx["error"] is None, f"Unexpected error: {ctx['error']}"
    assert ctx["result"]["status"] == status


@then(parsers.parse('the result date is "{date}"'))
def then_result_date(ctx, date):
    assert ctx["result"]["date"] == date


@then(parsers.parse("the captured list is {json_list}"))
def then_captured_list(ctx, json_list):
    expected = json.loads(json_list)
    actual = ctx["result"]["captured"]
    assert actual == expected, f"Expected captured={expected}, got {actual}"


# ---------------------------------------------------------------------------
# Then steps — validation errors
# ---------------------------------------------------------------------------

@then("a validation error is raised")
def then_validation_error(ctx):
    assert ctx["error"] is not None, "Expected a validation error but none was raised"


@then("no file is written")
def then_no_file_written(ctx):
    log_dir = ctx["vault_path"] / "logs" / "metrics"
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


@then(parsers.parse('the file "{rel_path}" contains {count:d} line'))
def then_file_lines_singular(ctx, rel_path, count):
    _assert_line_count(ctx, rel_path, count)


@then(parsers.parse('the file "{rel_path}" contains {count:d} lines'))
def then_file_lines_plural(ctx, rel_path, count):
    _assert_line_count(ctx, rel_path, count)


def _assert_line_count(ctx, rel_path, count):
    lines = [l for l in (ctx["vault_path"] / rel_path).read_text().splitlines() if l.strip()]
    assert len(lines) == count, f"Expected {count} lines, got {len(lines)}"


# ---------------------------------------------------------------------------
# Then steps — JSONL content
# ---------------------------------------------------------------------------

@then("the written entry has no null fields")
def then_no_null_fields(ctx):
    log_dir = ctx["vault_path"] / "logs" / "metrics"
    jsonl_files = list(log_dir.glob("*.jsonl"))
    assert jsonl_files, "No JSONL files found"
    for jsonl_file in jsonl_files:
        for line in jsonl_file.read_text().splitlines():
            if not line.strip():
                continue
            entry = json.loads(line)
            _check_no_nulls(entry)


def _check_no_nulls(obj):
    """Recursively assert no None values in a dict."""
    if isinstance(obj, dict):
        for key, val in obj.items():
            assert val is not None, f"Field '{key}' is null"
            _check_no_nulls(val)
    elif isinstance(obj, list):
        for item in obj:
            _check_no_nulls(item)
