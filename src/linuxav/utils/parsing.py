import yaml
from pathlib import Path
from typing import Any, Dict


def load_config(config_name: str = "default") -> Dict[str, Any]:
    config_dir = Path(__file__).parent.parent.parent.parent / "config"
    config_path = config_dir / f"{config_name}.yaml"
    
    if not config_path.exists():
        return {}
    
    with open(config_path) as f:
        return yaml.safe_load(f)


def get_config_value(key: str, default: Any = None) -> Any:
    config = load_config()
    keys = key.split(".")
    
    value = config
    for k in keys:
        if isinstance(value, dict):
            value = value.get(k)
        else:
            return default
    
    return value if value is not None else default
