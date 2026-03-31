from pathlib import Path
import os


def get_app_dir() -> Path:
    return Path(__file__).parent.parent.parent


def get_config_dir() -> Path:
    return get_app_dir() / "config"


def get_logs_dir() -> Path:
    return get_app_dir() / "logs"


def ensure_directories():
    logs_dir = get_logs_dir()
    logs_dir.mkdir(parents=True, exist_ok=True)
