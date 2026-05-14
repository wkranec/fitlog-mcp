"""Metrics logging tool for the fitlog vault."""
from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel, field_validator, model_validator

from fitlog.data.log import append_entry


# ---------------------------------------------------------------------------
# Pydantic models
# ---------------------------------------------------------------------------

class WeightMetric(BaseModel):
    value: float
    unit: str

    @field_validator("value")
    @classmethod
    def value_positive(cls, v: float) -> float:
        if v <= 0:
            raise ValueError("value must be positive")
        return v

    @field_validator("unit")
    @classmethod
    def unit_valid(cls, v: str) -> str:
        if v not in ("lbs", "kg"):
            raise ValueError("weight unit must be 'lbs' or 'kg'")
        return v


class HrvMetric(BaseModel):
    value: float
    unit: str
    source: str | None = None

    @field_validator("value")
    @classmethod
    def value_positive(cls, v: float) -> float:
        if v <= 0:
            raise ValueError("value must be positive")
        return v

    @field_validator("unit")
    @classmethod
    def unit_valid(cls, v: str) -> str:
        if v != "ms":
            raise ValueError("hrv unit must be 'ms'")
        return v


class SleepMetric(BaseModel):
    duration_hours: float
    quality: int | None = None
    source: str | None = None

    @field_validator("duration_hours")
    @classmethod
    def duration_positive(cls, v: float) -> float:
        if v <= 0:
            raise ValueError("duration_hours must be positive")
        return v

    @field_validator("quality")
    @classmethod
    def quality_range(cls, v: int | None) -> int | None:
        if v is not None and not (1 <= v <= 5):
            raise ValueError("sleep quality must be between 1 and 5")
        return v


class RestingHrMetric(BaseModel):
    value: int
    unit: str

    @field_validator("value")
    @classmethod
    def value_positive(cls, v: int) -> int:
        if v <= 0:
            raise ValueError("value must be positive")
        return v

    @field_validator("unit")
    @classmethod
    def unit_valid(cls, v: str) -> str:
        if v != "bpm":
            raise ValueError("resting_hr unit must be 'bpm'")
        return v


class BloodPressureMetric(BaseModel):
    systolic: int
    diastolic: int
    unit: str

    @field_validator("systolic", "diastolic")
    @classmethod
    def values_positive(cls, v: int) -> int:
        if v <= 0:
            raise ValueError("blood pressure values must be positive")
        return v

    @field_validator("unit")
    @classmethod
    def unit_valid(cls, v: str) -> str:
        if v != "mmHg":
            raise ValueError("blood_pressure unit must be 'mmHg'")
        return v


class Spo2Metric(BaseModel):
    value: float
    unit: str

    @field_validator("value")
    @classmethod
    def value_positive(cls, v: float) -> float:
        if v <= 0:
            raise ValueError("value must be positive")
        return v

    @field_validator("unit")
    @classmethod
    def unit_valid(cls, v: str) -> str:
        if v != "%":
            raise ValueError("spo2 unit must be '%'")
        return v


# ---------------------------------------------------------------------------
# Public tool function
# ---------------------------------------------------------------------------

def log_metrics(
    vault_path: Path,
    date: str,
    weight: dict | None = None,
    hrv: dict | None = None,
    sleep: dict | None = None,
    resting_hr: dict | None = None,
    blood_pressure: dict | None = None,
    spo2: dict | None = None,
) -> dict:
    """Log one or more metrics for a given date.

    Validates all provided metrics via Pydantic models, then appends a single
    entry to the annual JSONL file.  Returns a confirmation dict.
    """
    # Validate date
    from datetime import date as date_cls
    try:
        date_cls.fromisoformat(date)
    except (ValueError, TypeError) as exc:
        raise ValueError(f"Invalid date: {date!r}") from exc

    # Ensure at least one metric provided
    raw_metrics = {
        "weight": weight,
        "hrv": hrv,
        "sleep": sleep,
        "resting_hr": resting_hr,
        "blood_pressure": blood_pressure,
        "spo2": spo2,
    }
    provided = {k: v for k, v in raw_metrics.items() if v is not None}
    if not provided:
        raise ValueError("At least one metric must be provided")

    # Validate each metric via Pydantic
    validated: dict[str, dict] = {}
    model_map = {
        "weight": WeightMetric,
        "hrv": HrvMetric,
        "sleep": SleepMetric,
        "resting_hr": RestingHrMetric,
        "blood_pressure": BloodPressureMetric,
        "spo2": Spo2Metric,
    }
    for name, raw in provided.items():
        model_cls = model_map[name]
        # Let ValidationError propagate naturally
        instance = model_cls(**raw)
        # Exclude None fields so optional fields are not written
        validated[name] = instance.model_dump(exclude_none=True)

    # Build entry — only non-null metrics
    entry: dict = {"date": date, **validated}

    append_entry("metrics", entry, vault_path)

    return {
        "status": "ok",
        "date": date,
        "captured": list(validated.keys()),
    }
