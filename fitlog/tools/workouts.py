"""Workout logging tools for the fitlog vault."""
from __future__ import annotations

import re
from datetime import datetime, timezone
from pathlib import Path

import yaml
from pydantic import BaseModel, model_validator

from fitlog.data.log import append_entry


# ---------------------------------------------------------------------------
# Pydantic set-shape models
# ---------------------------------------------------------------------------

class BodyweightSet(BaseModel):
    """A set for a bodyweight exercise: only reps allowed."""

    model_config = {"extra": "forbid"}

    reps: int

    @model_validator(mode="after")
    def reps_positive(self) -> "BodyweightSet":
        if self.reps <= 0:
            raise ValueError("reps must be > 0")
        return self


class WeightedSet(BaseModel):
    """A set for a weighted exercise: reps, weight, weight_unit."""

    model_config = {"extra": "forbid"}

    reps: int
    weight: float
    weight_unit: str

    @model_validator(mode="after")
    def validate_fields(self) -> "WeightedSet":
        if self.reps <= 0:
            raise ValueError("reps must be > 0")
        if self.weight <= 0:
            raise ValueError("weight must be > 0")
        if self.weight_unit not in ("lbs", "kg"):
            raise ValueError("weight_unit must be 'lbs' or 'kg'")
        return self


class TimedSet(BaseModel):
    """A set for a timed exercise: only duration_seconds allowed."""

    model_config = {"extra": "forbid"}

    duration_seconds: float

    @model_validator(mode="after")
    def duration_positive(self) -> "TimedSet":
        if self.duration_seconds <= 0:
            raise ValueError("duration_seconds must be > 0")
        return self


_SET_MODEL_MAP = {
    "bodyweight": BodyweightSet,
    "weighted": WeightedSet,
    "timed": TimedSet,
}

VALID_LOAD_TYPES = frozenset(_SET_MODEL_MAP.keys())


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _load_exercises(vault_path: Path) -> dict:
    """Return a flat dict {exercise_id: definition} from all YAML files."""
    exercises_dir = vault_path / "exercises"
    if not exercises_dir.exists():
        return {}

    result: dict = {}
    for yaml_file in sorted(exercises_dir.glob("*.yaml")):
        with yaml_file.open() as fh:
            data = yaml.safe_load(fh) or {}
        if isinstance(data, dict):
            result.update(data)
    return result


# ---------------------------------------------------------------------------
# Public tool functions
# ---------------------------------------------------------------------------

def log_exercise(
    vault_path: Path,
    date: str,
    exercise_id: str,
    sets: list[dict],
    notes: str | None = None,
    raw_input: str | None = None,
) -> dict:
    """Log a single exercise session for the given date.

    Validates the date, looks up the exercise definition, validates each set
    against the load_type, then appends a JSONL entry.
    """
    from datetime import date as date_cls

    # 1. Validate date
    try:
        date_cls.fromisoformat(date)
    except (ValueError, TypeError) as exc:
        raise ValueError(f"Invalid date: {date!r}") from exc

    # 2. Load all exercises
    all_exercises = _load_exercises(vault_path)

    # 3. Check exercise exists
    if exercise_id not in all_exercises:
        raise ValueError(
            f"Exercise '{exercise_id}' not found. "
            "Use create_exercise() to add it first."
        )

    # 4. Get load_type
    definition = all_exercises[exercise_id]
    load_type = definition.get("load_type")
    set_model = _SET_MODEL_MAP.get(load_type)
    if set_model is None:
        raise ValueError(f"Unknown load_type '{load_type}' for exercise '{exercise_id}'")

    # 5. Validate sets is non-empty
    if not sets:
        raise ValueError("sets must be non-empty")

    # 6. Validate each set
    validated_sets: list[dict] = []
    for i, s in enumerate(sets):
        instance = set_model(**s)  # raises ValidationError on shape mismatch
        validated_sets.append(instance.model_dump())

    # 7. Build exercise object
    exercise_obj: dict = {
        "exercise_id": exercise_id,
        "sets": validated_sets,
    }
    if notes is not None:
        exercise_obj["notes"] = notes
    if raw_input is not None:
        exercise_obj["raw_input"] = raw_input

    # 8. Build entry
    date_compact = date.replace("-", "")
    workout_id = f"wo-{date_compact}"
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    entry: dict = {
        "id": workout_id,
        "date": date,
        "timestamp": timestamp,
        "exercises": [exercise_obj],
    }

    append_entry("workouts", entry, vault_path)

    return {
        "status": "ok",
        "date": date,
        "exercise_id": exercise_id,
        "sets_logged": len(validated_sets),
    }


def create_exercise(
    vault_path: Path,
    exercise_id: str,
    name: str,
    load_type: str,
) -> dict:
    """Create a new exercise definition and write it to a YAML file.

    The file is placed at ``{vault_path}/exercises/{exercise_id}.yaml``.
    """
    # 1. Validate load_type
    if load_type not in VALID_LOAD_TYPES:
        raise ValueError(
            f"Invalid load_type '{load_type}'. "
            f"Must be one of: {', '.join(sorted(VALID_LOAD_TYPES))}"
        )

    # 2. Validate exercise_id — only alphanumerics and underscores
    if not exercise_id or not re.fullmatch(r"[A-Za-z0-9_]+", exercise_id):
        raise ValueError(
            f"Invalid exercise_id '{exercise_id}'. "
            "Must be non-empty and contain only alphanumeric characters and underscores."
        )

    # 3. Check for duplicates
    all_exercises = _load_exercises(vault_path)
    if exercise_id in all_exercises:
        raise ValueError(f"Exercise '{exercise_id}' already exists.")

    # 4. Create parent directory and write YAML
    exercises_dir = vault_path / "exercises"
    exercises_dir.mkdir(parents=True, exist_ok=True)
    yaml_file = exercises_dir / f"{exercise_id}.yaml"

    content = f"{exercise_id}:\n  name: {name}\n  load_type: {load_type}\n"
    yaml_file.write_text(content)

    return {
        "status": "ok",
        "exercise_id": exercise_id,
        "name": name,
        "load_type": load_type,
        "file": str(yaml_file.relative_to(vault_path)),
    }
