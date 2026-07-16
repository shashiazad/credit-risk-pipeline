import os
import yaml
from typing import Dict, Any
# pyrefly: ignore [missing-import]
from src.utils.logger import get_logger

logger = get_logger(__name__)

def load_yaml(file_path: str) -> Dict[str, Any]:
    """
    Safely load and parse a YAML file.
    """
    if not os.path.exists(file_path):
        logger.error(f"Configuration file not found at path: {file_path}")
        raise FileNotFoundError(f"Configuration file not found at path: {file_path}")
        
    try:
        with open(file_path, "r") as stream:
            data = yaml.safe_load(stream)
            logger.info(f"Successfully loaded YAML file from {file_path}")
            return data
    except yaml.YAMLError as exc:
        logger.error(f"Failed to parse YAML file at {file_path}: {exc}")
        raise exc
