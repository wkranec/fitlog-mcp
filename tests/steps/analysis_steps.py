"""Step definitions for tests/features/metrics_analysis.feature."""
from __future__ import annotations

import json
from datetime import date
from pathlib import Path
from unittest.mock import patch

import pytest
from pytest_bdd import given, when, then, parsers, scenarios

from fitlog.analysis.metrics import weight_trend, hrv_trend, sleep_summary, resting_hr_trend

scenarios("../features/metrics_analysis.feature")


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

def _write_entry(vault_path: Path, entry: dict) -> None:
    entry_date = date.fromisoformat(entry["date"])
    log_file = vault_path / "logs" / "metrics" / f"{entry_date.year}.jsonl"
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


# ---------------------------------------------------------------------------
# Given steps
# ---------------------------------------------------------------------------

@given("a temporary vault directory")
def given_temp_vault(ctx):
    pass  # vault_path fixture provides the tmp directory


@given(parsers.parse('today is mocked to "{date_str}"'))
def given_today_mocked(ctx, date_str):
    ctx["today_mock"] = date_str


@given(parsers.parse('a metrics entry with date "{d}" and weight value {value:g} unit "{unit}"'))
def given_weight_entry(ctx, d, value, unit):
    _write_entry(ctx["vault_path"], {"date": d, "weight": {"value": value, "unit": unit}})


@given(parsers.parse('a metrics entry with date "{d}" and hrv value {value:g}'))
def given_hrv_entry(ctx, d, value):
    _write_entry(ctx["vault_path"], {"date": d, "hrv": {"value": value, "unit": "ms"}})


@given(parsers.parse('a metrics entry with date "{d}" and sleep duration {duration:g} quality {quality:d}'))
def given_sleep_entry_with_quality(ctx, d, duration, quality):
    _write_entry(ctx["vault_path"], {"date": d, "sleep": {"duration_hours": duration, "quality": quality}})


@given(parsers.parse('a metrics entry with date "{d}" and sleep duration {duration:g} no quality'))
def given_sleep_entry_no_quality(ctx, d, duration):
    _write_entry(ctx["vault_path"], {"date": d, "sleep": {"duration_hours": duration}})


@given(parsers.parse('a metrics entry with date "{d}" and resting_hr value {value:d}'))
def given_resting_hr_entry(ctx, d, value):
    _write_entry(ctx["vault_path"], {"date": d, "resting_hr": {"value": value, "unit": "bpm"}})


# ---------------------------------------------------------------------------
# When steps
# ---------------------------------------------------------------------------

@when("I call weight_trend with no date filter")
def when_weight_trend_no_filter(ctx):
    _call_fn(ctx, weight_trend, days=None)


@when(parsers.parse('I call weight_trend with days={days:d}'))
def when_weight_trend_days(ctx, days):
    _call_fn(ctx, weight_trend, days=days)


@when(parsers.parse('I call weight_trend with start_date "{start}" and end_date "{end}"'))
def when_weight_trend_range(ctx, start, end):
    _call_fn(ctx, weight_trend, start_date=start, end_date=end)


@when("I call hrv_trend with no date filter")
def when_hrv_trend_no_filter(ctx):
    _call_fn(ctx, hrv_trend, days=None)


@when("I call sleep_summary with no date filter")
def when_sleep_summary_no_filter(ctx):
    _call_fn(ctx, sleep_summary, days=None)


@when("I call resting_hr_trend with no date filter")
def when_resting_hr_trend_no_filter(ctx):
    _call_fn(ctx, resting_hr_trend, days=None)


# ---------------------------------------------------------------------------
# Then steps
# ---------------------------------------------------------------------------

@then(parsers.parse('the trend result field "{field}" equals int {value:d}'))
def then_field_int(ctx, field, value):
    actual = ctx["result"][field]
    assert actual == value, f"Expected {field}={value}, got {actual}"


@then(parsers.parse('the trend result field "{field}" equals float {value:g}'))
def then_field_float(ctx, field, value):
    actual = ctx["result"][field]
    assert actual == pytest.approx(value, rel=1e-3), f"Expected {field}={value}, got {actual}"


@then(parsers.parse('the trend result field "{field}" equals string "{value}"'))
def then_field_string(ctx, field, value):
    actual = ctx["result"][field]
    assert actual == value, f"Expected {field}='{value}', got '{actual}'"


@then(parsers.parse('the trend result field "{field}" is None'))
def then_field_none(ctx, field):
    actual = ctx["result"][field]
    assert actual is None, f"Expected {field}=None, got {actual!r}"
