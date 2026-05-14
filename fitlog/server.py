"""FastAPI server exposing fitlog tools and analysis as HTTP endpoints."""
from __future__ import annotations

import json
from pathlib import Path

from fastapi import Depends, FastAPI, Query
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ValidationError

from fitlog.config import settings
from fitlog.tools.metrics import log_metrics
from fitlog.tools.workouts import log_exercise, create_exercise
from fitlog.analysis.metrics import weight_trend, hrv_trend, sleep_summary, resting_hr_trend
from fitlog.analysis.workouts import (
    frequency_by_body_area,
    workout_streak,
    personal_records,
    incomplete_session_rate,
)

app = FastAPI(title="fitlog-mcp")


# ---------------------------------------------------------------------------
# Dependency
# ---------------------------------------------------------------------------

def get_vault_path() -> Path:
    return settings.fitlog_vault_path


# ---------------------------------------------------------------------------
# Exception handlers
# ---------------------------------------------------------------------------

@app.exception_handler(ValueError)
async def value_error_handler(request, exc):
    return JSONResponse(status_code=400, content={"detail": str(exc)})


@app.exception_handler(ValidationError)
async def validation_error_handler(request, exc):
    return JSONResponse(status_code=422, content=json.loads(exc.json()))


# ---------------------------------------------------------------------------
# Request models
# ---------------------------------------------------------------------------

class LogMetricsRequest(BaseModel):
    date: str
    weight: dict | None = None
    hrv: dict | None = None
    sleep: dict | None = None
    resting_hr: dict | None = None
    blood_pressure: dict | None = None
    spo2: dict | None = None


class LogExerciseRequest(BaseModel):
    date: str
    exercise_id: str
    sets: list[dict]
    notes: str | None = None
    raw_input: str | None = None


class CreateExerciseRequest(BaseModel):
    exercise_id: str
    name: str
    load_type: str


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------

@app.get("/health")
def health(vault_path: Path = Depends(get_vault_path)):
    return {"status": "ok", "vault": str(vault_path)}


# ---------------------------------------------------------------------------
# Metrics endpoints
# ---------------------------------------------------------------------------

@app.post("/v1/metrics/log")
def log_metrics_endpoint(body: LogMetricsRequest, vault_path: Path = Depends(get_vault_path)):
    return log_metrics(
        vault_path,
        date=body.date,
        weight=body.weight,
        hrv=body.hrv,
        sleep=body.sleep,
        resting_hr=body.resting_hr,
        blood_pressure=body.blood_pressure,
        spo2=body.spo2,
    )


# ---------------------------------------------------------------------------
# Workout endpoints
# ---------------------------------------------------------------------------

@app.post("/v1/workouts/log-exercise")
def log_exercise_endpoint(body: LogExerciseRequest, vault_path: Path = Depends(get_vault_path)):
    return log_exercise(
        vault_path,
        date=body.date,
        exercise_id=body.exercise_id,
        sets=body.sets,
        notes=body.notes,
        raw_input=body.raw_input,
    )


@app.post("/v1/workouts/create-exercise")
def create_exercise_endpoint(body: CreateExerciseRequest, vault_path: Path = Depends(get_vault_path)):
    return create_exercise(
        vault_path,
        exercise_id=body.exercise_id,
        name=body.name,
        load_type=body.load_type,
    )


# ---------------------------------------------------------------------------
# Analysis — metrics endpoints
# ---------------------------------------------------------------------------

@app.get("/v1/analysis/metrics/weight-trend")
def weight_trend_endpoint(
    vault_path: Path = Depends(get_vault_path),
    days: int = Query(default=60, ge=1),
    start_date: str | None = Query(default=None),
    end_date: str | None = Query(default=None),
):
    return weight_trend(vault_path, days=days, start_date=start_date, end_date=end_date)


@app.get("/v1/analysis/metrics/hrv-trend")
def hrv_trend_endpoint(
    vault_path: Path = Depends(get_vault_path),
    days: int = Query(default=60, ge=1),
    start_date: str | None = Query(default=None),
    end_date: str | None = Query(default=None),
):
    return hrv_trend(vault_path, days=days, start_date=start_date, end_date=end_date)


@app.get("/v1/analysis/metrics/sleep-summary")
def sleep_summary_endpoint(
    vault_path: Path = Depends(get_vault_path),
    days: int = Query(default=60, ge=1),
    start_date: str | None = Query(default=None),
    end_date: str | None = Query(default=None),
):
    return sleep_summary(vault_path, days=days, start_date=start_date, end_date=end_date)


@app.get("/v1/analysis/metrics/resting-hr-trend")
def resting_hr_trend_endpoint(
    vault_path: Path = Depends(get_vault_path),
    days: int = Query(default=60, ge=1),
    start_date: str | None = Query(default=None),
    end_date: str | None = Query(default=None),
):
    return resting_hr_trend(vault_path, days=days, start_date=start_date, end_date=end_date)


# ---------------------------------------------------------------------------
# Analysis — workout endpoints
# ---------------------------------------------------------------------------

@app.get("/v1/analysis/workouts/frequency-by-body-area")
def frequency_by_body_area_endpoint(
    vault_path: Path = Depends(get_vault_path),
    days: int = Query(default=60, ge=1),
    start_date: str | None = Query(default=None),
    end_date: str | None = Query(default=None),
):
    return frequency_by_body_area(
        vault_path,
        vault_path / "exercises",
        days=days,
        start_date=start_date,
        end_date=end_date,
    )


@app.get("/v1/analysis/workouts/streak")
def workout_streak_endpoint(
    vault_path: Path = Depends(get_vault_path),
    days: int = Query(default=60, ge=1),
    start_date: str | None = Query(default=None),
    end_date: str | None = Query(default=None),
):
    return workout_streak(vault_path, days=days, start_date=start_date, end_date=end_date)


@app.get("/v1/analysis/workouts/personal-records/{exercise_id}")
def personal_records_endpoint(
    exercise_id: str,
    vault_path: Path = Depends(get_vault_path),
    days: int = Query(default=60, ge=1),
    start_date: str | None = Query(default=None),
    end_date: str | None = Query(default=None),
):
    return personal_records(
        vault_path,
        exercise_id=exercise_id,
        days=days,
        start_date=start_date,
        end_date=end_date,
    )


@app.get("/v1/analysis/workouts/incomplete-session-rate")
def incomplete_session_rate_endpoint(
    vault_path: Path = Depends(get_vault_path),
    days: int = Query(default=60, ge=1),
    start_date: str | None = Query(default=None),
    end_date: str | None = Query(default=None),
):
    return incomplete_session_rate(vault_path, days=days, start_date=start_date, end_date=end_date)


# ---------------------------------------------------------------------------
# Dev runner
# ---------------------------------------------------------------------------

def run_dev():
    import uvicorn
    uvicorn.run("fitlog.server:app", host="0.0.0.0", port=8000, reload=True)
