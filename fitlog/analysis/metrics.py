"""Analytics functions over metrics history.

All functions read data via ``read_merged_list`` from ``fitlog.data.log``.
No direct file I/O is performed here.
"""
from __future__ import annotations

from datetime import date
from pathlib import Path

from fitlog.data.log import read_merged_list


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------

_LBS_TO_KG = 0.453592
_KG_TO_LBS = 2.20462


def _slope(xs: list[float], ys: list[float]) -> float | None:
    """Ordinary least squares slope.  Returns None when fewer than 2 points."""
    n = len(xs)
    if n < 2:
        return None
    sum_x = sum(xs)
    sum_y = sum(ys)
    sum_xy = sum(x * y for x, y in zip(xs, ys))
    sum_x2 = sum(x * x for x in xs)
    denom = n * sum_x2 - sum_x ** 2
    if denom == 0:
        return None
    return (n * sum_xy - sum_x * sum_y) / denom


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


def _round4(value: float) -> float:
    return round(value, 4)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def weight_trend(
    vault_path: Path,
    days: int | None = 60,
    start_date: str | None = None,
    end_date: str | None = None,
) -> dict:
    """Return weight trend statistics over the given window."""
    kwargs = _resolve_window(days, start_date, end_date)
    entries = read_merged_list("metrics", vault_path, **kwargs)

    # Filter to entries that have a weight field
    weight_entries = [e for e in entries if "weight" in e]

    if not weight_entries:
        return {
            "data_points": 0,
            "slope": None,
            "average": None,
            "min": None,
            "max": None,
            "delta": None,
            "unit": None,
            "start_date": None,
            "end_date": None,
        }

    # Sort by date
    weight_entries.sort(key=lambda e: e["date"])

    # Determine target unit from the first entry
    target_unit = weight_entries[0]["weight"]["unit"]

    def _to_target(value: float, unit: str) -> float:
        if unit == target_unit:
            return value
        if unit == "lbs" and target_unit == "kg":
            return value * _LBS_TO_KG
        if unit == "kg" and target_unit == "lbs":
            return value * _KG_TO_LBS
        return value

    values = [
        _to_target(e["weight"]["value"], e["weight"]["unit"])
        for e in weight_entries
    ]
    dates = [date.fromisoformat(e["date"]) for e in weight_entries]
    date0 = dates[0]
    xs = [(d - date0).days for d in dates]

    n = len(values)
    avg = _round4(sum(values) / n)
    mn = _round4(min(values))
    mx = _round4(max(values))
    slp = _slope(xs, values)
    if slp is not None:
        slp = _round4(slp)
    delta = _round4(values[-1] - values[0]) if n >= 2 else None

    return {
        "slope": slp,
        "average": avg,
        "min": mn,
        "max": mx,
        "delta": delta,
        "unit": target_unit,
        "data_points": n,
        "start_date": weight_entries[0]["date"],
        "end_date": weight_entries[-1]["date"],
    }


def hrv_trend(
    vault_path: Path,
    days: int | None = 60,
    start_date: str | None = None,
    end_date: str | None = None,
) -> dict:
    """Return HRV trend statistics over the given window."""
    kwargs = _resolve_window(days, start_date, end_date)
    entries = read_merged_list("metrics", vault_path, **kwargs)

    hrv_entries = [e for e in entries if "hrv" in e]

    if not hrv_entries:
        return {
            "data_points": 0,
            "slope": None,
            "average": None,
            "min": None,
            "max": None,
            "delta": None,
            "unit": None,
            "start_date": None,
            "end_date": None,
        }

    hrv_entries.sort(key=lambda e: e["date"])
    values = [e["hrv"]["value"] for e in hrv_entries]
    dates = [date.fromisoformat(e["date"]) for e in hrv_entries]
    date0 = dates[0]
    xs = [(d - date0).days for d in dates]

    n = len(values)
    avg = _round4(sum(values) / n)
    mn = _round4(min(values))
    mx = _round4(max(values))
    slp = _slope(xs, values)
    if slp is not None:
        slp = _round4(slp)
    delta = _round4(values[-1] - values[0]) if n >= 2 else None

    return {
        "slope": slp,
        "average": avg,
        "min": mn,
        "max": mx,
        "delta": delta,
        "unit": "ms",
        "data_points": n,
        "start_date": hrv_entries[0]["date"],
        "end_date": hrv_entries[-1]["date"],
    }


def sleep_summary(
    vault_path: Path,
    days: int | None = 60,
    start_date: str | None = None,
    end_date: str | None = None,
) -> dict:
    """Return sleep summary statistics over the given window."""
    kwargs = _resolve_window(days, start_date, end_date)
    entries = read_merged_list("metrics", vault_path, **kwargs)

    sleep_entries = [e for e in entries if "sleep" in e]

    if not sleep_entries:
        return {
            "average_duration_hours": None,
            "average_quality": None,
            "min_duration_hours": None,
            "max_duration_hours": None,
            "data_points": 0,
            "quality_data_points": 0,
        }

    durations = [e["sleep"]["duration_hours"] for e in sleep_entries]
    qualities = [e["sleep"]["quality"] for e in sleep_entries if "quality" in e["sleep"]]

    n = len(sleep_entries)
    avg_dur = _round4(sum(durations) / n)
    mn_dur = _round4(min(durations))
    mx_dur = _round4(max(durations))
    avg_qual = _round4(sum(qualities) / len(qualities)) if qualities else None

    return {
        "average_duration_hours": avg_dur,
        "average_quality": avg_qual,
        "min_duration_hours": mn_dur,
        "max_duration_hours": mx_dur,
        "data_points": n,
        "quality_data_points": len(qualities),
    }


def resting_hr_trend(
    vault_path: Path,
    days: int | None = 60,
    start_date: str | None = None,
    end_date: str | None = None,
) -> dict:
    """Return resting heart rate trend statistics over the given window."""
    kwargs = _resolve_window(days, start_date, end_date)
    entries = read_merged_list("metrics", vault_path, **kwargs)

    hr_entries = [e for e in entries if "resting_hr" in e]

    if not hr_entries:
        return {
            "data_points": 0,
            "slope": None,
            "average": None,
            "min": None,
            "max": None,
            "delta": None,
            "unit": None,
            "start_date": None,
            "end_date": None,
        }

    hr_entries.sort(key=lambda e: e["date"])
    values = [float(e["resting_hr"]["value"]) for e in hr_entries]
    dates = [date.fromisoformat(e["date"]) for e in hr_entries]
    date0 = dates[0]
    xs = [(d - date0).days for d in dates]

    n = len(values)
    avg = _round4(sum(values) / n)
    mn = _round4(min(values))
    mx = _round4(max(values))
    slp = _slope(xs, values)
    if slp is not None:
        slp = _round4(slp)
    delta = _round4(values[-1] - values[0]) if n >= 2 else None

    return {
        "slope": slp,
        "average": avg,
        "min": mn,
        "max": mx,
        "delta": delta,
        "unit": "bpm",
        "data_points": n,
        "start_date": hr_entries[0]["date"],
        "end_date": hr_entries[-1]["date"],
    }
