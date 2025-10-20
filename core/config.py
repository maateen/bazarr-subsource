"""
Configuration management for Bazarr SubSource integration.
"""

import configparser
import logging
import logging.handlers
import sys
from pathlib import Path

logger = logging.getLogger(__name__)


def load_config():
    """
    Load configuration from config file.

    Returns:
        Configuration dictionary or None if error
    """
    # Config file path
    config_dir = Path.home() / ".config" / "bazarr-subsource"
    config_file = config_dir / "config.cfg"

    # Create config directory if it doesn't exist
    config_dir.mkdir(parents=True, exist_ok=True)

    # Create default config file if it doesn't exist
    if not config_file.exists():
        create_default_config(config_file)
        print(f"Created default config file at: {config_file}")
        print("Please edit the configuration file with your settings and run again.")
        sys.exit(1)

    # Load configuration
    config = configparser.ConfigParser()
    try:
        config.read(config_file)

        config_dict = {
            "bazarr_url": config.get("bazarr", "url"),
            "api_key": config.get("bazarr", "api_key"),
            "username": config.get("auth", "username"),
            "password": config.get("auth", "password"),
            "subsource_api_url": config.get("subsource", "api_url"),
            "download_directory": config.get("download", "directory"),
            "movies_enabled": config.getboolean("movies", "enabled", fallback=True),
            "episodes_enabled": config.getboolean("episodes", "enabled", fallback=True),
            "episodes_search_patterns": config.get(
                "episodes",
                "search_patterns",
                fallback="season_episode,episode_title,scene_name",
            ),
            "log_level": config.get("logging", "level", fallback="INFO"),
            "log_file": config.get("logging", "file", fallback="bazarr_subsource.log"),
        }

        logger.info(f"Configuration loaded from: {config_file}")
        return config_dict

    except (configparser.Error, FileNotFoundError) as e:
        print(f"Error loading configuration: {e}")
        sys.exit(1)


def create_default_config(config_file: Path):
    """Create a default configuration file."""
    config = configparser.ConfigParser()

    config["bazarr"] = {
        "url": "https://yourbazarr.example.com",
        "api_key": "your_api_key_here",
    }

    config["auth"] = {"username": "your_username", "password": "your_password"}

    config["subsource"] = {"api_url": "https://api.subsource.net/v1"}

    config["download"] = {"directory": "/tmp/downloaded_subtitles"}

    config["movies"] = {"enabled": "true"}

    config["episodes"] = {
        "enabled": "true",
        "search_patterns": "season_episode,episode_title,scene_name",
    }

    config["logging"] = {"level": "INFO", "file": "/var/log/bazarr_subsource.log"}

    with open(config_file, "w") as f:
        # Write header comments
        f.write("# Bazarr SubSource Integration Configuration\n")
        f.write("# Edit this file with your actual settings\n\n")

        # Write bazarr section
        f.write("[bazarr]\n")
        f.write("url = https://yourbazarr.example.com\n")
        f.write("api_key = your_api_key_here\n\n")

        # Write auth section with comments
        f.write("[auth]\n")
        f.write(
            "# Only needed if you have a reverse proxy with basic auth "
            "in front of Bazarr\n"
        )
        f.write(
            "# Leave empty or remove this section if connecting directly to Bazarr\n"
        )
        f.write("username = your_username\n")
        f.write("password = your_password\n\n")

        # Write remaining sections
        f.write("[subsource]\n")
        f.write("api_url = https://api.subsource.net/v1\n\n")

        f.write("[download]\n")
        f.write("directory = /tmp/downloaded_subtitles\n\n")

        f.write("[movies]\n")
        f.write("# Enable movie subtitle downloads\n")
        f.write("enabled = true\n\n")

        f.write("[episodes]\n")
        f.write("# Enable TV series episode subtitle downloads\n")
        f.write("enabled = true\n")
        f.write("# Search patterns: season_episode,episode_title,scene_name\n")
        f.write("search_patterns = season_episode,episode_title,scene_name\n\n")

        f.write("[logging]\n")
        f.write("level = INFO\n")
        f.write("file = /var/log/bazarr_subsource.log\n")


def setup_logging(log_level: str, log_file: str):
    """
    Setup logging configuration optimized for cron execution with rotation.

    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR)
        log_file: Log file path
    """
    level = getattr(logging, log_level.upper(), logging.INFO)

    # Create formatters
    detailed_formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )

    # Create log directory if it doesn't exist
    log_path = Path(log_file)
    log_path.parent.mkdir(parents=True, exist_ok=True)

    # Rotating file handler - 10MB max, keep 5 old files
    file_handler = logging.handlers.RotatingFileHandler(
        log_file,
        maxBytes=10 * 1024 * 1024,
        backupCount=5,
        encoding="utf-8",  # 10MB
    )
    file_handler.setLevel(level)
    file_handler.setFormatter(detailed_formatter)

    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(level)

    # Clear existing handlers to avoid duplicates
    root_logger.handlers.clear()
    root_logger.addHandler(file_handler)

    # Suppress excessive logging from requests library for cron
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("requests").setLevel(logging.WARNING)
