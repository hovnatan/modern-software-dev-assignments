from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

_APP_ROOT = Path(__file__).resolve().parents[1]


@dataclass(frozen=True, slots=True)
class Settings:
    """Application paths and static configuration (no secrets)."""

    app_root: Path
    data_dir: Path
    db_path: Path
    frontend_dir: Path


@lru_cache
def get_settings() -> Settings:
    root = _APP_ROOT
    data = root / "data"
    return Settings(
        app_root=root,
        data_dir=data,
        db_path=data / "app.db",
        frontend_dir=root / "frontend",
    )
