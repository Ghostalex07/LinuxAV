from pathlib import Path
from typing import Optional

DANGEROUS_DIRS = ("/proc", "/sys", "/dev", "/run", "/snap")


def is_valid_path(path: str) -> bool:
    try:
        p = Path(path).resolve()
        return p.exists()
    except (OSError, RuntimeError):
        return False


def is_valid_directory(path: str) -> bool:
    try:
        p = Path(path).resolve()
        return p.is_dir()
    except (OSError, RuntimeError):
        return False


def is_safe_path(path: str) -> bool:
    try:
        p = Path(path).resolve()
        for dangerous in DANGEROUS_DIRS:
            if str(p) == dangerous or str(p).startswith(dangerous + "/"):
                return False
        return True
    except (OSError, RuntimeError):
        return False


def validate_scan_path(path: str) -> tuple[bool, Optional[str]]:
    if not is_valid_path(path):
        return False, f"La ruta no existe: {path}"
    
    if not is_valid_directory(path):
        return False, f"La ruta no es un directorio: {path}"
    
    if not is_safe_path(path):
        return False, f"Directorio no permitido por seguridad: {path}"
    
    return True, None


def get_safe_default_path() -> str:
    return str(Path.home())
