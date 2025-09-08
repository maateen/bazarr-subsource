"""
Tests for core.config module.
"""

import configparser
import logging
import os
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from core.config import create_default_config, load_config, setup_logging


class TestConfig(unittest.TestCase):
    """Test cases for configuration management."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.config_file = Path(self.temp_dir) / "test_config.cfg"

    def tearDown(self):
        """Clean up test fixtures."""
        if self.config_file.exists():
            self.config_file.unlink()
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_create_default_config(self):
        """Test creating a default configuration file."""
        create_default_config(self.config_file)

        self.assertTrue(self.config_file.exists())

        # Verify the config content
        config = configparser.ConfigParser()
        config.read(self.config_file)

        # Check all required sections exist
        expected_sections = [
            "bazarr",
            "auth",
            "subsource",
            "download",
            "movies",
            "episodes",
            "logging",
        ]
        for section in expected_sections:
            self.assertIn(section, config.sections())

        # Check specific values
        self.assertEqual(config.get("bazarr", "url"), "https://yourbazarr.example.com")
        self.assertEqual(
            config.get("subsource", "api_url"), "https://api.subsource.net/v1"
        )
        self.assertEqual(config.get("logging", "level"), "INFO")

    @patch("core.config.Path.home")
    @patch("core.config.create_default_config")
    @patch("sys.exit")
    def test_load_config_creates_default_when_missing(
        self, mock_exit, mock_create, mock_home
    ):
        """Test that load_config creates default config when file doesn't exist."""
        mock_home.return_value = Path(self.temp_dir)
        config_dir = Path(self.temp_dir) / ".config" / "bazarr-subsource"
        config_file = config_dir / "config.cfg"

        # Make create_default_config also create a valid minimal config
        def create_valid_config(path):
            config = configparser.ConfigParser()
            config.add_section("bazarr")
            config.set("bazarr", "url", "test")
            config.set("bazarr", "api_key", "test")
            config.add_section("auth")
            config.set("auth", "username", "test")
            config.set("auth", "password", "test")
            config.add_section("subsource")
            config.set("subsource", "api_url", "test")
            config.add_section("download")
            config.set("download", "directory", "test")
            config.add_section("logging")
            config.set("logging", "level", "INFO")
            config.set("logging", "file", "test.log")
            with open(path, "w") as f:
                config.write(f)

        mock_create.side_effect = create_valid_config

        load_config()

        mock_create.assert_called_once_with(config_file)
        mock_exit.assert_called_once_with(1)

    @patch("core.config.Path.home")
    def test_load_config_success(self, mock_home):
        """Test successful configuration loading."""
        mock_home.return_value = Path(self.temp_dir)
        config_dir = Path(self.temp_dir) / ".config" / "bazarr-subsource"
        config_dir.mkdir(parents=True)
        config_file = config_dir / "config.cfg"

        # Create a test config file
        create_default_config(config_file)

        result = load_config()

        self.assertIsInstance(result, dict)
        expected_keys = [
            "bazarr_url",
            "api_key",
            "username",
            "password",
            "subsource_api_url",
            "download_directory",
            "movies_enabled",
            "episodes_enabled",
            "episodes_search_patterns",
            "log_level",
            "log_file",
        ]
        for key in expected_keys:
            self.assertIn(key, result)

    @patch("core.config.Path.home")
    @patch("sys.exit")
    def test_load_config_handles_config_error(self, mock_exit, mock_home):
        """Test load_config handles configuration errors."""
        mock_home.return_value = Path(self.temp_dir)
        config_dir = Path(self.temp_dir) / ".config" / "bazarr-subsource"
        config_dir.mkdir(parents=True)
        config_file = config_dir / "config.cfg"

        # Create invalid config file
        with open(config_file, "w") as f:
            f.write("invalid config content")

        load_config()

        mock_exit.assert_called_once_with(1)

    def test_setup_logging(self):
        """Test logging setup."""
        log_file = os.path.join(self.temp_dir, "test.log")

        # Clear any existing handlers
        root_logger = logging.getLogger()
        for handler in root_logger.handlers[:]:
            root_logger.removeHandler(handler)

        setup_logging("INFO", log_file)

        # Check that file handler was added
        self.assertTrue(
            any(
                isinstance(handler, logging.FileHandler)
                for handler in root_logger.handlers
            )
        )

        # Test logging works
        test_logger = logging.getLogger("test")
        test_logger.info("Test message")

        # Verify log file was created and contains message
        self.assertTrue(os.path.exists(log_file))
        with open(log_file, "r") as f:
            content = f.read()
            self.assertIn("Test message", content)

    def test_setup_logging_different_levels(self):
        """Test logging setup with different log levels."""
        log_file = os.path.join(self.temp_dir, "test_debug.log")

        # Clear any existing handlers
        root_logger = logging.getLogger()
        for handler in root_logger.handlers[:]:
            root_logger.removeHandler(handler)

        setup_logging("DEBUG", log_file)

        # Check that DEBUG level is set
        self.assertEqual(root_logger.level, logging.DEBUG)

    def test_setup_logging_suppresses_requests(self):
        """Test that requests library logging is suppressed."""
        log_file = os.path.join(self.temp_dir, "test_requests.log")

        setup_logging("INFO", log_file)

        # Check that urllib3 and requests loggers are set to WARNING
        urllib3_logger = logging.getLogger("urllib3")
        requests_logger = logging.getLogger("requests")

        self.assertEqual(urllib3_logger.level, logging.WARNING)
        self.assertEqual(requests_logger.level, logging.WARNING)

    def test_setup_logging_rotation(self):
        """Test that log rotation is properly configured."""
        log_file = os.path.join(self.temp_dir, "test_rotation.log")

        setup_logging("INFO", log_file)

        # Get the root logger and check its handlers
        root_logger = logging.getLogger()

        # Should have exactly one handler (the rotating file handler)
        self.assertEqual(len(root_logger.handlers), 1)

        # Check that it's a RotatingFileHandler
        handler = root_logger.handlers[0]
        self.assertIsInstance(handler, logging.handlers.RotatingFileHandler)

        # Check rotation settings
        self.assertEqual(handler.maxBytes, 10 * 1024 * 1024)  # 10MB
        self.assertEqual(handler.backupCount, 5)

    def test_episode_configuration_defaults(self):
        """Test that episode configuration has proper defaults."""
        # Create basic config without episode section
        config = configparser.ConfigParser()
        config["bazarr"] = {"url": "http://test", "api_key": "test"}
        config["auth"] = {"username": "test", "password": "test"}
        config["subsource"] = {"api_url": "http://test"}
        config["download"] = {"directory": "/tmp"}
        config["logging"] = {"level": "INFO", "file": "test.log"}

        # Test fallback values for episodes
        episodes_enabled = config.getboolean("episodes", "enabled", fallback=True)
        episodes_patterns = config.get(
            "episodes",
            "search_patterns",
            fallback="season_episode,episode_title,scene_name",
        )

        self.assertTrue(episodes_enabled)  # Default should be True
        self.assertEqual(episodes_patterns, "season_episode,episode_title,scene_name")


if __name__ == "__main__":
    unittest.main()
