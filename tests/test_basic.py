import os
from src.utils.logger import get_logger
from src.utils.helpers import load_yaml

logger = get_logger(__name__)

def test_environment_variables():
    """
    Test that env variables are loaded correctly from .env
    """
    env = os.getenv("ENV")
    assert env is not None, "ENV variable should be loaded from .env"
    logger.info(f"Test environment is: {env}")

def test_load_config():
    """
    Test that pipeline configuration YAML can be loaded
    """
    config = load_yaml("config/config.yaml")
    assert config is not None, "Config should load successfully"
    assert "pipeline" in config, "Config should contain 'pipeline' section"
    assert config["pipeline"]["name"] == "loan_risk_pipeline"
    logger.info(f"Loaded pipeline name: {config['pipeline']['name']}")
