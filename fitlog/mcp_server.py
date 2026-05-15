"""fitlog MCP server.

Exposes fitness logging and analysis tools via the Model Context Protocol.
All tools read vault_path from the FITLOG_VAULT_PATH environment variable.

Usage with uvx:
    uvx fitlog-mcp

MCP client config:
    {
      "mcpServers": {
        "fitlog": {"command": "uvx", "args": ["fitlog-mcp"]}
      }
    }
"""
from __future__ import annotations

from pathlib import Path

from fastmcp import FastMCP

from fitlog.config import settings
from fitlog.tools.metrics import log_metrics
from fitlog.tools.workouts import log_exercise, create_exercise as _create_exercise
from fitlog.analysis.metrics import weight_trend, hrv_trend, sleep_summary, resting_hr_trend
from fitlog.analysis.workouts import (
    frequency_by_body_area,
    workout_streak,
    personal_records,
    incomplete_session_rate,
)

mcp = FastMCP("fitlog-mcp")

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _vault() -> Path:
    return settings.fitlog_vault_path


# ---------------------------------------------------------------------------
# Metrics logging tools
# ---------------------------------------------------------------------------

@mcp.tool()
def log_weight(date: str, value: float, unit: str) -> dict:
    """Log a body weight measurement for the given date.

    Args:
        date: ISO 8601 date string, e.g. "2025-05-13"
        value: Weight as a positive number
        unit: "lbs" or "kg"
    """
    return log_metrics(_vault(), date=date, weight={"value": value, "unit": unit})


@mcp.tool()
def log_hrv(date: str, value: float, source: str | None = None) -> dict:
    """Log a heart rate variability (HRV) reading for the given date.

    Args:
        date: ISO 8601 date string, e.g. "2025-05-13"
        value: HRV value in milliseconds (positive number)
        source: Optional device or app name, e.g. "apple_watch"
    """
    hrv: dict = {"value": value, "unit": "ms"}
    if source is not None:
        hrv["source"] = source
    return log_metrics(_vault(), date=date, hrv=hrv)


@mcp.tool()
def log_sleep(
    date: str,
    duration_hours: float,
    quality: int | None = None,
    source: str | None = None,
) -> dict:
    """Log a sleep record for the given date.

    Args:
        date: ISO 8601 date string, e.g. "2025-05-13"
        duration_hours: Total sleep duration in hours (positive number)
        quality: Optional subjective sleep quality, integer 1 (poor) to 5 (excellent)
        source: Optional device or app name, e.g. "oura"
    """
    sleep: dict = {"duration_hours": duration_hours}
    if quality is not None:
        sleep["quality"] = quality
    if source is not None:
        sleep["source"] = source
    return log_metrics(_vault(), date=date, sleep=sleep)


@mcp.tool()
def log_resting_hr(date: str, value: int) -> dict:
    """Log a resting heart rate measurement for the given date.

    Args:
        date: ISO 8601 date string, e.g. "2025-05-13"
        value: Resting heart rate in beats per minute (positive integer)
    """
    return log_metrics(_vault(), date=date, resting_hr={"value": value, "unit": "bpm"})


@mcp.tool()
def log_blood_pressure(date: str, systolic: int, diastolic: int) -> dict:
    """Log a blood pressure reading for the given date.

    Args:
        date: ISO 8601 date string, e.g. "2025-05-13"
        systolic: Systolic pressure in mmHg (positive integer)
        diastolic: Diastolic pressure in mmHg (positive integer)
    """
    return log_metrics(
        _vault(),
        date=date,
        blood_pressure={"systolic": systolic, "diastolic": diastolic, "unit": "mmHg"},
    )


@mcp.tool()
def log_spo2(date: str, value: float) -> dict:
    """Log a blood oxygen saturation (SpO2) reading for the given date.

    Args:
        date: ISO 8601 date string, e.g. "2025-05-13"
        value: SpO2 percentage, e.g. 98.0 (positive number, typically 90-100)
    """
    return log_metrics(_vault(), date=date, spo2={"value": value, "unit": "%"})


# ---------------------------------------------------------------------------
# Workout tools
# ---------------------------------------------------------------------------

@mcp.tool()
def create_exercise(exercise_id: str, name: str, load_type: str) -> dict:
    """Create a new exercise definition in the vault.

    Call this before logging an exercise that doesn't exist yet.
    Exercises are stored as YAML files in the vault's exercises directory.

    Args:
        exercise_id: Unique identifier using only letters, numbers, and underscores,
                     e.g. "ring_rows" or "barbell_press"
        name: Human-readable name, e.g. "Ring Rows"
        load_type: "bodyweight", "weighted", or "timed"
    """
    return _create_exercise(_vault(), exercise_id=exercise_id, name=name, load_type=load_type)


@mcp.tool()
def log_bodyweight_exercise(
    date: str,
    exercise_id: str,
    reps: list[int],
    notes: str | None = None,
    raw_input: str | None = None,
) -> dict:
    """Log a bodyweight exercise session (no external load).

    Use this for exercises like pull-ups, push-ups, ring rows, dips.
    If the exercise_id doesn't exist yet, call create_exercise first.

    Args:
        date: ISO 8601 date string, e.g. "2025-05-13"
        exercise_id: Exercise identifier, e.g. "ring_rows"
        reps: Reps completed per set as a list, e.g. [10, 8, 8] for three sets
        notes: Optional free-text note about this exercise
        raw_input: Optional original voice or text input from the user
    """
    sets = [{"reps": r} for r in reps]
    return log_exercise(_vault(), date=date, exercise_id=exercise_id, sets=sets,
                        notes=notes, raw_input=raw_input)


@mcp.tool()
def log_weighted_exercise(
    date: str,
    exercise_id: str,
    reps: list[int],
    weights: list[float],
    weight_unit: str,
    notes: str | None = None,
    raw_input: str | None = None,
) -> dict:
    """Log a weighted exercise session (barbell, dumbbell, machine, etc.).

    reps and weights must be the same length — one entry per set.
    Use this for exercises like barbell press, squat, deadlift, curls.
    If the exercise_id doesn't exist yet, call create_exercise first.

    Args:
        date: ISO 8601 date string, e.g. "2025-05-13"
        exercise_id: Exercise identifier, e.g. "barbell_press"
        reps: Reps per set, e.g. [8, 6, 6] for three sets
        weights: Weight per set in the same order, e.g. [135.0, 145.0, 145.0]
        weight_unit: "lbs" or "kg" — applies to all sets
        notes: Optional free-text note about this exercise
        raw_input: Optional original voice or text input from the user
    """
    if len(reps) != len(weights):
        raise ValueError(f"reps and weights must be the same length ({len(reps)} vs {len(weights)})")
    sets = [{"reps": r, "weight": w, "weight_unit": weight_unit} for r, w in zip(reps, weights)]
    return log_exercise(_vault(), date=date, exercise_id=exercise_id, sets=sets,
                        notes=notes, raw_input=raw_input)


@mcp.tool()
def log_timed_exercise(
    date: str,
    exercise_id: str,
    duration_seconds: list[float],
    notes: str | None = None,
    raw_input: str | None = None,
) -> dict:
    """Log a timed exercise session (holds, planks, intervals).

    Use this for exercises like plank, wall sit, dead hang.
    If the exercise_id doesn't exist yet, call create_exercise first.

    Args:
        date: ISO 8601 date string, e.g. "2025-05-13"
        exercise_id: Exercise identifier, e.g. "plank"
        duration_seconds: Duration of each set in seconds, e.g. [45.0, 45.0, 30.0]
        notes: Optional free-text note about this exercise
        raw_input: Optional original voice or text input from the user
    """
    sets = [{"duration_seconds": d} for d in duration_seconds]
    return log_exercise(_vault(), date=date, exercise_id=exercise_id, sets=sets,
                        notes=notes, raw_input=raw_input)


@mcp.tool()
def log_breathwork_exercise(
    date: str,
    exercise_id: str,
    duration_minutes: int,
    duration_seconds_remainder: int = 0,
    notes: str | None = None,
    raw_input: str | None = None,
) -> dict:
    """Log a breath work session.

    Use this for box breathing, body scans, super ventilation, and similar practices.
    If the exercise_id doesn't exist yet, call create_exercise first with load_type='breathwork'.

    Args:
        date: ISO 8601 date string, e.g. "2025-05-13"
        exercise_id: Exercise identifier, e.g. "box_breathing"
        duration_minutes: Total whole minutes of the session, e.g. 10
        duration_seconds_remainder: Additional seconds beyond the full minutes (0-59), e.g. 30
        notes: Optional free-text note about this session
        raw_input: Optional original voice or text input from the user
    """
    total_seconds = duration_minutes * 60 + duration_seconds_remainder
    sets = [{"duration_seconds": float(total_seconds)}]
    return log_exercise(_vault(), date=date, exercise_id=exercise_id, sets=sets,
                        notes=notes, raw_input=raw_input)


# ---------------------------------------------------------------------------
# Analysis tools
# ---------------------------------------------------------------------------

@mcp.tool()
def get_weight_trend(
    days: int = 60,
    start_date: str | None = None,
    end_date: str | None = None,
) -> dict:
    """Return weight trend statistics over a time window.

    Returns slope (lbs or kg per day), average, min, max, delta, and data point count.
    If start_date or end_date is provided, the days parameter is ignored.

    Args:
        days: Number of days to look back from today (default 60)
        start_date: Optional ISO date string for the start of the window
        end_date: Optional ISO date string for the end of the window
    """
    return weight_trend(_vault(), days=days, start_date=start_date, end_date=end_date)


@mcp.tool()
def get_hrv_trend(
    days: int = 60,
    start_date: str | None = None,
    end_date: str | None = None,
) -> dict:
    """Return HRV trend statistics over a time window.

    Returns slope (ms per day), average, min, max, delta, and data point count.
    If start_date or end_date is provided, the days parameter is ignored.

    Args:
        days: Number of days to look back from today (default 60)
        start_date: Optional ISO date string for the start of the window
        end_date: Optional ISO date string for the end of the window
    """
    return hrv_trend(_vault(), days=days, start_date=start_date, end_date=end_date)


@mcp.tool()
def get_sleep_summary(
    days: int = 60,
    start_date: str | None = None,
    end_date: str | None = None,
) -> dict:
    """Return sleep summary statistics over a time window.

    Returns average duration, average quality (if logged), min/max duration,
    and data point counts.
    If start_date or end_date is provided, the days parameter is ignored.

    Args:
        days: Number of days to look back from today (default 60)
        start_date: Optional ISO date string for the start of the window
        end_date: Optional ISO date string for the end of the window
    """
    return sleep_summary(_vault(), days=days, start_date=start_date, end_date=end_date)


@mcp.tool()
def get_resting_hr_trend(
    days: int = 60,
    start_date: str | None = None,
    end_date: str | None = None,
) -> dict:
    """Return resting heart rate trend statistics over a time window.

    Returns slope (bpm per day), average, min, max, delta, and data point count.
    If start_date or end_date is provided, the days parameter is ignored.

    Args:
        days: Number of days to look back from today (default 60)
        start_date: Optional ISO date string for the start of the window
        end_date: Optional ISO date string for the end of the window
    """
    return resting_hr_trend(_vault(), days=days, start_date=start_date, end_date=end_date)


@mcp.tool()
def get_workout_frequency(
    days: int = 60,
    start_date: str | None = None,
    end_date: str | None = None,
) -> dict:
    """Return workout frequency broken down by primary body area over a time window.

    Requires exercises to have body_areas defined in their YAML files.
    Returns a dict of body area names to set counts.
    If start_date or end_date is provided, the days parameter is ignored.

    Args:
        days: Number of days to look back from today (default 60)
        start_date: Optional ISO date string for the start of the window
        end_date: Optional ISO date string for the end of the window
    """
    return frequency_by_body_area(
        _vault(), _vault() / "exercises",
        days=days, start_date=start_date, end_date=end_date,
    )


@mcp.tool()
def get_workout_streak(
    days: int = 60,
    start_date: str | None = None,
    end_date: str | None = None,
) -> dict:
    """Return the current workout streak and related stats over a time window.

    A streak counts consecutive calendar days that include at least one logged exercise.
    If start_date or end_date is provided, the days parameter is ignored.

    Args:
        days: Number of days to look back from today (default 60)
        start_date: Optional ISO date string for the start of the window
        end_date: Optional ISO date string for the end of the window
    """
    return workout_streak(_vault(), days=days, start_date=start_date, end_date=end_date)


@mcp.tool()
def get_personal_records(
    exercise_id: str,
    days: int = 60,
    start_date: str | None = None,
    end_date: str | None = None,
) -> dict:
    """Return personal records for a specific exercise over a time window.

    A PR is defined as the session with the highest total work (max weight × reps
    across all sets). Only applies to weighted exercises.
    If start_date or end_date is provided, the days parameter is ignored.

    Args:
        exercise_id: Exercise identifier to look up, e.g. "barbell_press"
        days: Number of days to look back from today (default 60)
        start_date: Optional ISO date string for the start of the window
        end_date: Optional ISO date string for the end of the window
    """
    return personal_records(_vault(), exercise_id=exercise_id,
                            days=days, start_date=start_date, end_date=end_date)


@mcp.tool()
def get_session_count(
    days: int = 60,
    start_date: str | None = None,
    end_date: str | None = None,
) -> dict:
    """Return the total number of logged workout sessions over a time window.

    If start_date or end_date is provided, the days parameter is ignored.

    Args:
        days: Number of days to look back from today (default 60)
        start_date: Optional ISO date string for the start of the window
        end_date: Optional ISO date string for the end of the window
    """
    return incomplete_session_rate(_vault(), days=days, start_date=start_date, end_date=end_date)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
