import logging
import os
from .config import setup_directories

def setup_logger(name="DubbingPipeline", log_file="pipeline.log"):
    """Set up and return a logger with standard formatting."""
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)

    if not logger.handlers:
        # Create formatter
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s', datefmt='%Y-%m-%d %H:%M:%S')

        # Console handler
        ch = logging.StreamHandler()
        ch.setLevel(logging.INFO)
        ch.setFormatter(formatter)
        logger.addHandler(ch)

        # File handler
        # Ensure log file can be created safely
        try:
            fh = logging.FileHandler(log_file)
            fh.setLevel(logging.DEBUG)
            fh.setFormatter(formatter)
            logger.addHandler(fh)
        except Exception as e:
            print(f"Warning: Could not create log file {log_file} ({e})")

    return logger

logger = setup_logger()

def initialize_project_environment():
    """Ensure all required folders are ready before starting the pipeline."""
    logger.info("Initializing project environment...")
    setup_directories()
    logger.info("Project directories ready.")
