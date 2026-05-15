"""Read and parse vault/goals.yaml."""
from __future__ import annotations

from pathlib import Path
import yaml


def load_goals(vault_path: Path) -> dict[str, dict]:
    """Return {goal_id: goal_dict} from goals.yaml. Empty dict if file missing."""
    goals_file = vault_path / "goals.yaml"
    if not goals_file.exists():
        return {}
    with goals_file.open() as fh:
        data = yaml.safe_load(fh) or {}
    return data.get("goals", {})


def get_goal(vault_path: Path, goal_id: str) -> dict:
    """Return a single goal by ID. Raises KeyError if not found."""
    goals = load_goals(vault_path)
    if goal_id not in goals:
        raise KeyError(f"Goal '{goal_id}' not found in goals.yaml")
    return goals[goal_id]
