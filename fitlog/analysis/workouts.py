"""Analytics functions over workout history.

All functions read data via ``read_merged_list`` from ``fitlog.data.log``.
No direct file I/O is performed here.
"""
from __future__ import annotations

from datetime import date, timedelta
from pathlib import Path

import yaml

from fitlog.data.log import read_merged_list


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------

def _resolve_window(days: int | None, start_date: str | None, end_date: str | None) -> dict:
    """Return kwargs to pass to read_merged_list based on the window params."""
    if start_date is not None or end_date is not None:
        kwargs: dict = {}
        if start_date:
            kwargs["start_date"] = start_date
        if end_date:
            kwargs["end_date"] = end_date
        return kwargs
    if days is None:
        return {}
    return {"days": days}


def _window_days(days: int, start_date: str | None, end_date: str | None) -> int:
    """Return the number of calendar days in the resolved window."""
    if start_date is not None or end_date is not None:
        if start_date and end_date:
            s = date.fromisoformat(start_date)
            e = date.fromisoformat(end_date)
            return max(1, (e - s).days + 1)
        # Only one bound provided — use days as fallback
        return days
    return days


def _load_exercise_defs(exercise_yaml_dir: Path) -> dict:
    """Load all *.yaml exercise files and return a mapping of exercise_id -> definition."""
    defs: dict = {}
    if not exercise_yaml_dir.exists():
        return defs
    for yaml_file in exercise_yaml_dir.glob("*.yaml"):
        try:
            with yaml_file.open() as fh:
                data = yaml.safe_load(fh)
            if isinstance(data, dict):
                ex_id = data.get("id") or yaml_file.stem
                defs[ex_id] = data
        except Exception:
            pass
    return defs


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def frequency_by_body_area(
    vault_path: Path,
    exercise_yaml_dir: Path,
    days: int = 60,
    start_date: str | None = None,
    end_date: str | None = None,
) -> dict:
    """Count sets performed per primary body area across all workouts in the window."""
    kwargs = _resolve_window(days, start_date, end_date)
    workouts = read_merged_list("workouts", vault_path, **kwargs)
    wdays = _window_days(days, start_date, end_date)

    if not workouts:
        return {"window_days": wdays, "body_areas": {}}

    exercise_defs = _load_exercise_defs(exercise_yaml_dir)
    body_area_counts: dict[str, int] = {}

    for workout in workouts:
        for exercise in workout.get("exercises", []):
            ex_id = exercise.get("exercise_id")
            if ex_id not in exercise_defs:
                continue
            ex_def = exercise_defs[ex_id]
            primary_areas = (
                ex_def.get("body_areas", {}) or {}
            ).get("primary", []) or []
            if not primary_areas:
                continue
            set_count = len(exercise.get("sets", []))
            for area in primary_areas:
                body_area_counts[area] = body_area_counts.get(area, 0) + set_count

    return {"window_days": wdays, "body_areas": body_area_counts}


def workout_streak(
    vault_path: Path,
    days: int = 60,
    start_date: str | None = None,
    end_date: str | None = None,
) -> dict:
    """Count consecutive workout days ending at the last workout date in the window."""
    kwargs = _resolve_window(days, start_date, end_date)
    workouts = read_merged_list("workouts", vault_path, **kwargs)

    if not workouts:
        return {
            "current_streak": 0,
            "last_workout_date": None,
            "total_workout_days": 0,
        }

    # Collect distinct workout dates
    workout_dates = sorted(
        {date.fromisoformat(wo["date"]) for wo in workouts}
    )

    total_workout_days = len(workout_dates)
    last_workout_date = workout_dates[-1]

    # Walk backwards from last_workout_date counting consecutive days
    streak = 1
    for i in range(len(workout_dates) - 2, -1, -1):
        if workout_dates[i + 1] - workout_dates[i] == timedelta(days=1):
            streak += 1
        else:
            break

    return {
        "current_streak": streak,
        "last_workout_date": last_workout_date.isoformat(),
        "total_workout_days": total_workout_days,
    }


def personal_records(
    vault_path: Path,
    exercise_id: str,
    days: int = 60,
    start_date: str | None = None,
    end_date: str | None = None,
) -> dict:
    """Find the personal record for a specific exercise by maximum total work per session."""
    kwargs = _resolve_window(days, start_date, end_date)
    workouts = read_merged_list("workouts", vault_path, **kwargs)

    sessions_analyzed = 0
    pr_date: str | None = None
    pr_total_work: float | None = None
    pr_sets: list | None = None

    # Group workouts by date and collect sets for the target exercise
    sessions: dict[str, list] = {}
    for workout in workouts:
        wo_date = workout.get("date", "")
        for exercise in workout.get("exercises", []):
            if exercise.get("exercise_id") == exercise_id:
                if wo_date not in sessions:
                    sessions[wo_date] = []
                sessions[wo_date].extend(exercise.get("sets", []))

    for session_date, sets in sorted(sessions.items()):
        sessions_analyzed += 1
        # Determine total work for this session
        total_work = 0.0
        for s in sets:
            if "weight" in s and "reps" in s:
                total_work += s["weight"] * s["reps"]
            elif "duration_seconds" in s:
                total_work += s["duration_seconds"]
            elif "reps" in s:
                total_work += s["reps"]

        if pr_total_work is None or total_work > pr_total_work:
            pr_total_work = total_work
            pr_date = session_date
            pr_sets = sets

    return {
        "exercise_id": exercise_id,
        "pr_date": pr_date,
        "pr_total_work": pr_total_work,
        "pr_sets": pr_sets,
        "sessions_analyzed": sessions_analyzed,
    }


def incomplete_session_rate(
    vault_path: Path,
    days: int = 60,
    start_date: str | None = None,
    end_date: str | None = None,
) -> dict:
    """Return session completeness stats.

    Per project spec, the ``completed`` field was removed — all logged workouts
    are considered complete.  This function is kept for API completeness and
    always reports 0 incomplete sessions.
    """
    kwargs = _resolve_window(days, start_date, end_date)
    workouts = read_merged_list("workouts", vault_path, **kwargs)

    # Count distinct sessions (workout objects)
    total_sessions = len(workouts)

    return {
        "total_sessions": total_sessions,
        "incomplete_sessions": 0,
        "incomplete_rate": 0.0,
    }
