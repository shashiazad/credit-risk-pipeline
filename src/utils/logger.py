import os
import logging
import logging.config
import yaml
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def setup_logging(default_path="config/logging.yaml", default_level=logging.INFO, env_key="LOG_CFG"):
    """
    Setup logging configuration.
    It reads the logging config from YAML. If anything fails, it uses basicConfig.
    It ensures the logs directory exists before configuring the RotatingFileHandler.
    """
    # Ensure logs directory exists
    Path("logs").mkdir(exist_ok=True)
    
    path = default_path
    value = os.getenv(env_key, None)
    if value:
        path = value
        
    if os.path.exists(path):
        with open(path, "rt") as f:
            try:
                config = yaml.safe_load(f.read())
                logging.config.dictConfig(config)
            except Exception as e:
                print(f"Error in Logging Configuration from file {path}, using default config: {e}")
                logging.basicConfig(level=default_level)
    else:
        print(f"Logging configuration file {path} not found, using basicConfig.")
        logging.basicConfig(level=default_level)

def get_logger(name: str) -> logging.Logger:
    """
    Helper function to get a preconfigured logger.
    """
    return logging.getLogger(name)
