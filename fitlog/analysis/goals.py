"""Analytics functions for goal progress tracking.

All functions read data via ``read_merged_list`` and ``read_merged`` from
``fitlog.data.log``. No direct file I/O is performed here.
"""
from __future__ import annotations

import operator as op_module
from calendar import monthrange
from datetime import date, timedelta
from pathlib import Path

from fitlog.data.goals import get_goal, load_goals
from fitlog.data.log import read_merged, read_merged_list


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


_OPS = {
    ">=": op_module.ge,
    "<=": op_module.le,
    ">": op_module.gt,
    "<": op_module.lt,
    "==": op_module.eq,
}


def _meets(value: float, operator: str, target: float) -> bool:
    fn = _OPS.get(operator)
    if fn is None:
        raise ValueError(f"Unsupported operator: {operator!r}")
    return fn(value, target)


def _today() -> date:
    return date.today()


def _week_bounds(d: date) -> tuple[date, date]:
    """Return (monday, sunday) for the ISO week containing d."""
    monday = d - timedelta(days=d.weekday())
    sunday = monday + timedelta(days=6)
    return monday, sunday


def _month_bounds(d: date) -> tuple[date, date]:
    """Return (first_day, last_day) for the calendar month containing d."""
    first = d.replace(day=1)
    last_day = monthrange(d.year, d.month)[1]
    last = d.replace(day=last_day)
    return first, last


def _iso_week_key(d: date) -> str:
    """Return YYYY-WNN for the ISO week of d."""
    iso = d.isocalendar()
    return f"{iso[0]}-W{iso[1]:02d}"


def _month_key(d: date) -> str:
    return d.strftime("%Y-%m")


# ---------------------------------------------------------------------------
# Per-date evaluation helpers
# ---------------------------------------------------------------------------

def _eval_metric_day(entry: dict, goal: dict) -> dict:
    """Evaluate a metric goal for a single date entry.

    Returns {"met": bool|None, "value": float|None}.
    """
    metric_key = goal["metric"]
    field = goal["field"]
    if metric_key not in entry:
        return {"met": None, "value": None}
    metric_data = entry[metric_key]
    if not isinstance(metric_data, dict) or field not in metric_data:
        return {"met": None, "value": None}
    value = float(metric_data[field])
    met = _meets(value, goal["operator"], float(goal["target"]))
    return {"met": met, "value": value}


def _eval_activity_day(workouts_for_date: list[dict], goal: dict) -> dict:
    """Evaluate an activity goal for a single date's workout list.

    Returns {"met": bool|None, "value": float|None} where value is total minutes.
    """
    exercise_ids = goal.get("exercise_ids") or []
    total_seconds = 0.0
    found_any = False

    for workout in workouts_for_date:
        for exercise in workout.get("exercises", []):
            ex_id = exercise.get("exercise_id", "")
            if exercise_ids and ex_id not in exercise_ids:
                continue
            for s in exercise.get("sets", []):
                dur = s.get("duration_seconds")
                if dur is not None:
                    total_seconds += float(dur)
                    found_any = True

    if not found_any and not workouts_for_date:
        return {"met": None, "value": None}
    if not found_any:
        # Workouts exist but no matching exercises with duration
        # Check if exercise_ids filter leaves nothing or no duration-bearing sets
        # Still return a value of 0 if there are workouts
        has_matching = False
        for workout in workouts_for_date:
            for exercise in workout.get("exercises", []):
                ex_id = exercise.get("exercise_id", "")
                if exercise_ids and ex_id not in exercise_ids:
                    continue
                has_matching = True
                break
            if has_matching:
                break
        if not has_matching and exercise_ids:
            return {"met": None, "value": None}
        # Has matching exercises but none with duration_seconds
        total_minutes = 0.0
        met = _meets(total_minutes, goal["operator"], float(goal["target_minutes"]))
        return {"met": met, "value": total_minutes}

    total_minutes = total_seconds / 60.0
    met = _meets(total_minutes, goal["operator"], float(goal["target_minutes"]))
    return {"met": met, "value": total_minutes}


# ---------------------------------------------------------------------------
# Streak calculation
# ---------------------------------------------------------------------------

def _compute_streak_daily(
    date_results: dict[date, dict],
    as_of_date: date,
) -> int:
    """Count consecutive met days ending at as_of_date.

    No-data days (met=None) are transparent — they don't break or count.
    """
    streak = 0
    d = as_of_date
    while True:
        if d not in date_results:
            # No data — go back one more day
            d -= timedelta(days=1)
            # Avoid infinite loop — stop after a reasonable gap
            # We'll track how many consecutive no-data days
            continue
        res = date_results[d]
        if res["met"] is True:
            streak += 1
            d -= timedelta(days=1)
        elif res["met"] is False:
            break
        else:
            # met is None — transparent
            d -= timedelta(days=1)

        # Safety: stop if we've gone back too far without finding data
        # We rely on the window being finite; the loop will terminate
        # when d goes before any data in date_results.
        if d < min(date_results.keys()):
            break

    return streak


def _compute_streak_daily_safe(
    date_results: dict[date, dict],
    as_of_date: date,
) -> int:
    """Safe streak computation that handles empty date_results."""
    if not date_results:
        return 0
    return _compute_streak_daily(date_results, as_of_date)


# ---------------------------------------------------------------------------
# Frequency goal period helpers
# ---------------------------------------------------------------------------

def _compute_frequency_periods(
    workout_dates_by_date: dict[str, list],  # date_str -> list of workouts
    goal: dict,
    window_start: date,
    window_end: date,
    today: date,
) -> list[dict]:
    """Compute period-by-period frequency results.

    Returns list of period dicts sorted ascending.
    """
    exercise_ids = goal.get("exercise_ids") or []
    period = goal.get("period", "week")
    target = int(goal["target"])
    operator = goal["operator"]

    # Collect qualifying workout days in window
    qualifying_days: set[date] = set()
    for date_str, workouts in workout_dates_by_date.items():
        d = date.fromisoformat(date_str)
        if d < window_start or d > window_end:
            continue
        for workout in workouts:
            for exercise in workout.get("exercises", []):
                ex_id = exercise.get("exercise_id", "")
                if exercise_ids and ex_id not in exercise_ids:
                    continue
                qualifying_days.add(d)
                break

    # Build periods that overlap the window
    periods: dict[str, dict] = {}

    # Enumerate all dates in window and assign to periods
    d = window_start
    while d <= window_end:
        if period == "week":
            pkey = _iso_week_key(d)
            pstart, pend = _week_bounds(d)
        else:  # month
            pkey = _month_key(d)
            pstart, pend = _month_bounds(d)

        if pkey not in periods:
            periods[pkey] = {
                "period": pkey,
                "period_start": pstart.isoformat(),
                "period_end": pend.isoformat(),
                "days": set(),
                "complete": today > pend,
            }
        # A period in progress includes today
        if today <= pend and today >= pstart:
            periods[pkey]["complete"] = False

        if d in qualifying_days:
            periods[pkey]["days"].add(d)

        if period == "week":
            d += timedelta(days=1)
        else:
            d += timedelta(days=1)

    results = []
    for pkey in sorted(periods.keys()):
        p = periods[pkey]
        value = len(p["days"])
        met = _meets(value, operator, target)
        results.append({
            "period": pkey,
            "period_start": p["period_start"],
            "period_end": p["period_end"],
            "met": met,
            "value": value,
            "complete": p["complete"],
        })
    return results


def _compute_frequency_streak(period_results: list[dict]) -> int:
    """Count consecutive complete periods met, ending at most recent complete period."""
    complete_periods = [p for p in period_results if p["complete"]]
    if not complete_periods:
        return 0
    streak = 0
    for p in reversed(complete_periods):
        if p["met"]:
            streak += 1
        else:
            break
    return streak


def _pct_met_last_n_periods(period_results: list[dict], n: int) -> float:
    complete = [p for p in period_results if p["complete"]]
    last_n = complete[-n:] if len(complete) > n else complete
    if not last_n:
        return 0.0
    met_count = sum(1 for p in last_n if p["met"])
    return met_count / len(last_n)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def list_goals(vault_path: Path) -> dict:
    """Return all goals with their id, description, and type. Empty dict if no goals file."""
    goals = load_goals(vault_path)
    if not goals:
        return {"goals": []}
    result = []
    for goal_id, goal in goals.items():
        result.append({
            "goal_id": goal_id,
            "description": goal.get("description", ""),
            "type": goal.get("type", ""),
        })
    return {"goals": result}


def check_goal_status(
    vault_path: Path,
    goal_id: str,
    as_of_date: str | None = None,
) -> dict:
    """Check the current status of a goal."""
    goal = get_goal(vault_path, goal_id)
    today = date.fromisoformat(as_of_date) if as_of_date else _today()
    as_of_str = today.isoformat()

    goal_type = goal.get("type", "")

    # Always read last 30 days for pct_met calculation
    thirty_days_ago = today - timedelta(days=29)
    window_kwargs_30 = {
        "start_date": thirty_days_ago.isoformat(),
        "end_date": today.isoformat(),
    }

    if goal_type == "metric":
        entries = read_merged_list("metrics", vault_path, **window_kwargs_30)
        # Build date -> eval result
        date_results: dict[date, dict] = {}
        for entry in entries:
            d = date.fromisoformat(entry["date"])
            date_results[d] = _eval_metric_day(entry, goal)

        today_result = date_results.get(today, {"met": None, "value": None})
        streak = _compute_streak_daily_safe(date_results, today)

        days_with_data = sum(1 for r in date_results.values() if r["met"] is not None)
        days_met = sum(1 for r in date_results.values() if r["met"] is True)
        pct_met = days_met / days_with_data if days_with_data > 0 else 0.0

        return {
            "goal_id": goal_id,
            "description": goal.get("description", ""),
            "type": "metric",
            "as_of_date": as_of_str,
            "met": today_result["met"],
            "value": today_result["value"],
            "target": float(goal["target"]),
            "operator": goal["operator"],
            "streak": streak,
            "pct_met_last_30_days": round(pct_met, 4),
            "days_with_data": days_with_data,
        }

    elif goal_type == "activity":
        workouts_merged = read_merged("workouts", vault_path, **window_kwargs_30)
        date_results: dict[date, dict] = {}
        for date_str, workouts_list in workouts_merged.items():
            d = date.fromisoformat(date_str)
            date_results[d] = _eval_activity_day(workouts_list, goal)

        today_result = date_results.get(today, {"met": None, "value": None})
        streak = _compute_streak_daily_safe(date_results, today)

        days_with_data = sum(1 for r in date_results.values() if r["met"] is not None)
        days_met = sum(1 for r in date_results.values() if r["met"] is True)
        pct_met = days_met / days_with_data if days_with_data > 0 else 0.0

        return {
            "goal_id": goal_id,
            "description": goal.get("description", ""),
            "type": "activity",
            "as_of_date": as_of_str,
            "met": today_result["met"],
            "value": today_result["value"],
            "target": float(goal["target_minutes"]),
            "operator": goal["operator"],
            "streak": streak,
            "pct_met_last_30_days": round(pct_met, 4),
            "days_with_data": days_with_data,
        }

    elif goal_type == "frequency":
        period = goal.get("period", "week")
        if period == "week":
            pstart, pend = _week_bounds(today)
        else:
            pstart, pend = _month_bounds(today)

        # For status, read enough data for current period + streak history (12 periods back)
        if period == "week":
            lookback_days = 12 * 7 + 7
        else:
            lookback_days = 12 * 31 + 31

        window_start = today - timedelta(days=lookback_days)
        window_kwargs = {
            "start_date": window_start.isoformat(),
            "end_date": today.isoformat(),
        }
        workouts_merged = read_merged("workouts", vault_path, **window_kwargs)

        period_results = _compute_frequency_periods(
            workouts_merged, goal,
            window_start=window_start,
            window_end=today,
            today=today,
        )

        # Current period
        if period == "week":
            current_key = _iso_week_key(today)
        else:
            current_key = _month_key(today)

        current = next((p for p in period_results if p["period"] == current_key), None)
        if current is None:
            current = {
                "period": current_key,
                "period_start": pstart.isoformat(),
                "period_end": pend.isoformat(),
                "met": _meets(0, goal["operator"], int(goal["target"])),
                "value": 0,
                "complete": today > pend,
            }

        streak = _compute_frequency_streak(period_results)
        pct = _pct_met_last_n_periods(period_results, 12)

        return {
            "goal_id": goal_id,
            "description": goal.get("description", ""),
            "type": "frequency",
            "as_of_date": as_of_str,
            "period": period,
            "period_start": current["period_start"],
            "period_end": current["period_end"],
            "met": current["met"],
            "value": current["value"],
            "target": int(goal["target"]),
            "operator": goal["operator"],
            "streak": streak,
            "pct_met_last_12_periods": round(pct, 4),
        }

    else:
        raise ValueError(f"Unknown goal type: {goal_type!r}")


def get_goal_history(
    vault_path: Path,
    goal_id: str,
    days: int = 30,
    start_date: str | None = None,
    end_date: str | None = None,
) -> dict:
    """Get day-by-day or period-by-period history for a goal."""
    goal = get_goal(vault_path, goal_id)
    goal_type = goal.get("type", "")
    today = _today()

    window_kwargs = _resolve_window(days, start_date, end_date)

    if goal_type == "metric":
        entries = read_merged_list("metrics", vault_path, **window_kwargs)
        history = []
        for entry in sorted(entries, key=lambda e: e["date"]):
            r = _eval_metric_day(entry, goal)
            if r["met"] is None:
                continue
            history.append({
                "date": entry["date"],
                "met": r["met"],
                "value": r["value"],
            })
        return {
            "goal_id": goal_id,
            "description": goal.get("description", ""),
            "type": "metric",
            "history": history,
        }

    elif goal_type == "activity":
        workouts_merged = read_merged("workouts", vault_path, **window_kwargs)
        history = []
        for date_str in sorted(workouts_merged.keys()):
            workouts_list = workouts_merged[date_str]
            r = _eval_activity_day(workouts_list, goal)
            if r["met"] is None:
                continue
            history.append({
                "date": date_str,
                "met": r["met"],
                "value": r["value"],
            })
        return {
            "goal_id": goal_id,
            "description": goal.get("description", ""),
            "type": "activity",
            "history": history,
        }

    elif goal_type == "frequency":
        period = goal.get("period", "week")

        # Determine window bounds
        if start_date is not None or end_date is not None:
            window_start = date.fromisoformat(start_date) if start_date else date(2000, 1, 1)
            window_end = date.fromisoformat(end_date) if end_date else today
        else:
            window_end = today
            window_start = today - timedelta(days=days - 1)

        workouts_merged = read_merged("workouts", vault_path, **window_kwargs)

        period_results = _compute_frequency_periods(
            workouts_merged, goal,
            window_start=window_start,
            window_end=window_end,
            today=today,
        )

        history = []
        for p in period_results:
            history.append({
                "period": p["period"],
                "period_start": p["period_start"],
                "period_end": p["period_end"],
                "met": p["met"],
                "value": p["value"],
                "complete": p["complete"],
            })

        return {
            "goal_id": goal_id,
            "description": goal.get("description", ""),
            "type": "frequency",
            "history": history,
        }

    else:
        raise ValueError(f"Unknown goal type: {goal_type!r}")
