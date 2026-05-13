"""JSONL log read/write operations for the fitlog vault.

All functions accept an explicit vault_path so they can be tested in isolation
without relying on the global Settings object.
"""
from __future__ import annotations

import json
from datetime import date, timedelta
from pathlib import Path


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _deep_merge(base: dict, override: dict) -> dict:
    """Recursively merge *override* into *base*.

    Rules:
    - Scalar values: override wins.
    - Dict values: merged recursively.
    - List values: concatenated (base + override).
    """
    result = dict(base)
    for key, val in override.items():
        if key in result:
            if isinstance(result[key], dict) and isinstance(val, dict):
                result[key] = _deep_merge(result[key], val)
            elif isinstance(result[key], list) and isinstance(val, list):
                result[key] = result[key] + val
            else:
                result[key] = val
        else:
            result[key] = val
    return result


def _log_dir(log_type: str, vault_path: Path) -> Path:
    return vault_path / "logs" / log_type


def _annual_file(log_type: str, year: int, vault_path: Path) -> Path:
    return _log_dir(log_type, vault_path) / f"{year}.jsonl"


def _years_for_range(start: date, end: date) -> list[int]:
    """Return a sorted list of calendar years that overlap [start, end]."""
    return list(range(start.year, end.year + 1))


def _date_filter(
    entry_date: date,
    start: date | None,
    end: date | None,
) -> bool:
    if start is not None and entry_date < start:
        return False
    if end is not None and entry_date > end:
        return False
    return True


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def append_entry(log_type: str, entry: dict, vault_path: Path) -> None:
    """Append *entry* as a JSON line to the appropriate annual JSONL file.

    The target file is ``{vault_path}/logs/{log_type}/{year}.jsonl`` where
    *year* is extracted from ``entry["date"]``.
    """
    entry_date = date.fromisoformat(entry["date"])
    target = _annual_file(log_type, entry_date.year, vault_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("a") as fh:
        fh.write(json.dumps(entry) + "\n")


def read_merged(
    log_type: str,
    vault_path: Path,
    days: int | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
    years: list[int] | None = None,
) -> dict:
    """Read JSONL log files and return merged entries keyed by date string.

    Parameters
    ----------
    log_type:
        "metrics" or "workouts".
    vault_path:
        Root vault directory.
    days:
        Return entries from the last *days* days inclusive of today.
        Mutually exclusive with *years*.
    start_date:
        ISO date string; inclusive lower bound. Mutually exclusive with *years*.
    end_date:
        ISO date string; inclusive upper bound. Mutually exclusive with *years*.
    years:
        List of years to read without any date filtering.

    Returns
    -------
    For "metrics": ``{date_str: merged_dict}``
    For "workouts": ``{date_str: [merged_workout, ...]}``
    """
    today = date.today()

    # Resolve which annual files to load and what date bounds to apply.
    filter_start: date | None = None
    filter_end: date | None = None

    if years is not None:
        # Explicit year list — no date filtering
        target_years = sorted(set(years))
    elif days is not None:
        filter_end = today
        filter_start = today - timedelta(days=days - 1)
        target_years = _years_for_range(filter_start, filter_end)
    else:
        # Optional start/end without explicit years
        if start_date:
            filter_start = date.fromisoformat(start_date)
        if end_date:
            filter_end = date.fromisoformat(end_date)

        if filter_start is not None and filter_end is not None:
            target_years = _years_for_range(filter_start, filter_end)
        elif filter_start is not None:
            # From start_date to far future; enumerate existing files >= start year
            target_years = None  # resolved below from available files
        elif filter_end is not None:
            target_years = None  # resolved below from available files
        else:
            target_years = None  # read all available files

    log_dir = _log_dir(log_type, vault_path)

    if target_years is None:
        # Discover years from existing files
        if not log_dir.exists():
            return {}
        target_years = sorted(
            int(p.stem) for p in log_dir.glob("*.jsonl") if p.stem.isdigit()
        )

    result: dict = {}

    for year in target_years:
        path = _annual_file(log_type, year, vault_path)
        if not path.exists():
            continue
        with path.open() as fh:
            for raw_line in fh:
                raw_line = raw_line.strip()
                if not raw_line:
                    continue
                try:
                    entry = json.loads(raw_line)
                except json.JSONDecodeError:
                    continue

                entry_date = date.fromisoformat(entry["date"])

                if not _date_filter(entry_date, filter_start, filter_end):
                    continue

                date_str = entry["date"]

                if log_type == "metrics":
                    if date_str not in result:
                        result[date_str] = dict(entry)
                    else:
                        result[date_str] = _deep_merge(result[date_str], entry)

                elif log_type == "workouts":
                    if date_str not in result:
                        result[date_str] = {}
                    workout_id = entry.get("id")
                    if workout_id is None:
                        # No id — treat as standalone entry using a unique key
                        import uuid
                        workout_id = str(uuid.uuid4())
                        result[date_str][workout_id] = dict(entry)
                    elif workout_id in result[date_str]:
                        result[date_str][workout_id] = _deep_merge(
                            result[date_str][workout_id], entry
                        )
                    else:
                        result[date_str][workout_id] = dict(entry)

    # Convert workouts id-keyed dicts to lists
    if log_type == "workouts":
        return {d: list(workouts.values()) for d, workouts in result.items()}

    return result


def read_merged_list(
    log_type: str,
    vault_path: Path,
    days: int | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
) -> list:
    """Same as read_merged but returns a flat list sorted ascending by date.

    For "metrics": list of merged dicts (each includes a ``date`` key).
    For "workouts": flat list of all workout objects across dates.
    """
    merged = read_merged(
        log_type,
        vault_path,
        days=days,
        start_date=start_date,
        end_date=end_date,
    )

    if log_type == "metrics":
        items = list(merged.values())
        # Ensure each item has a date key (it should from the log entry)
        items.sort(key=lambda x: x.get("date", ""))
        return items

    elif log_type == "workouts":
        flat: list[dict] = []
        for date_str in sorted(merged.keys()):
            for workout in merged[date_str]:
                # Ensure date is present on each workout object
                wo = dict(workout)
                if "date" not in wo:
                    wo["date"] = date_str
                flat.append(wo)
        return flat

    return []
