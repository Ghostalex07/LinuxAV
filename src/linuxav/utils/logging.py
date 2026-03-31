import logging
import logging.config
import yaml
from pathlib import Path


def setup_logging():
    config_path = Path(__file__).parent.parent.parent.parent / "config" / "logging.yaml"
    
    if config_path.exists():
        with open(config_path) as f:
            config = yaml.safe_load(f)
            logging.config.dictConfig(config)
    else:
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)
