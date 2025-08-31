"""
Tests for main run.py module.
"""

import unittest
from unittest.mock import Mock, patch

import run


class TestRun(unittest.TestCase):
    """Test cases for main execution module."""

    @patch("run.load_config")
    @patch("run.setup_logging")
    @patch("run.Bazarr")
    @patch("run.SubSourceDownloader")
    @patch("builtins.print")
    def test_main_no_movies(
        self,
        mock_print,
        mock_downloader,
        mock_bazarr_class,
        mock_setup_logging,
        mock_load_config,
    ):
        """Test main function when no movies are missing subtitles."""
        # Mock configuration
        mock_config = {
            "log_level": "INFO",
            "log_file": "test.log",
            "bazarr_url": "https://test.bazarr.com",
            "api_key": "test_key",
            "username": "test_user",
            "password": "test_pass",
            "subsource_api_url": "https://api.test.com",
            "download_directory": "/tmp",
        }
        mock_load_config.return_value = mock_config

        # Mock Bazarr client
        mock_bazarr = Mock()
        mock_bazarr.get_wanted_movies.return_value = {"data": []}
        mock_bazarr_class.return_value = mock_bazarr

        # Mock logging setup
        mock_logger = Mock()
        with patch("run.logging.getLogger", return_value=mock_logger):
            run.main()

        # Verify configuration was loaded
        mock_load_config.assert_called_once()
        mock_setup_logging.assert_called_once_with("INFO", "test.log")

        # Verify Bazarr client was created and called
        mock_bazarr_class.assert_called_once_with(
            "https://test.bazarr.com", "test_key", "test_user", "test_pass"
        )
        mock_bazarr.get_wanted_movies.assert_called_once()

        # Verify appropriate messages were printed
        print_calls = [call[0][0] for call in mock_print.call_args_list]
        self.assertIn("No movies are currently missing subtitles!", print_calls)

    @patch("run.load_config")
    @patch("run.setup_logging")
    @patch("run.Bazarr")
    @patch("run.SubSourceDownloader")
    @patch("run.time.sleep")
    @patch("run.os.remove")
    @patch("builtins.print")
    def test_main_with_movies_success(
        self,
        mock_print,
        mock_remove,
        mock_sleep,
        mock_downloader_class,
        mock_bazarr_class,
        mock_setup_logging,
        mock_load_config,
    ):
        """Test main function with successful subtitle processing."""
        # Mock configuration
        mock_config = {
            "log_level": "INFO",
            "log_file": "test.log",
            "bazarr_url": "https://test.bazarr.com",
            "api_key": "test_key",
            "username": "test_user",
            "password": "test_pass",
            "subsource_api_url": "https://api.test.com",
            "download_directory": "/tmp",
        }
        mock_load_config.return_value = mock_config

        # Mock movies data
        movies_data = {
            "data": [
                {
                    "title": "Test Movie",
                    "radarrId": 123,
                    "missing_subtitles": [
                        {"name": "English", "code2": "en", "forced": False, "hi": False}
                    ],
                }
            ]
        }

        # Mock Bazarr client
        mock_bazarr = Mock()
        mock_bazarr.get_wanted_movies.return_value = movies_data
        mock_bazarr.upload_subtitle_to_bazarr.return_value = True
        mock_bazarr_class.return_value = mock_bazarr

        # Mock SubSource downloader
        mock_downloader = Mock()
        mock_downloader.get_subtitle_for_movie.return_value = (["/tmp/test.srt"], 0)
        mock_downloader_class.return_value = mock_downloader

        # Mock logging
        mock_logger = Mock()
        with patch("run.logging.getLogger", return_value=mock_logger):
            run.main()

        # Verify downloader was created
        mock_downloader_class.assert_called_once_with(
            "https://api.test.com", "/tmp", mock_bazarr
        )

        # Verify subtitle processing
        mock_downloader.get_subtitle_for_movie.assert_called_once()
        mock_bazarr.upload_subtitle_to_bazarr.assert_called_once_with(
            123, "/tmp/test.srt", "en", False, False
        )

        # Verify file cleanup
        mock_remove.assert_called_once_with("/tmp/test.srt")

        # Verify success logging
        mock_logger.info.assert_called()

    @patch("run.load_config")
    @patch("run.setup_logging")
    @patch("run.Bazarr")
    @patch("builtins.print")
    def test_main_bazarr_api_failure(
        self, mock_print, mock_bazarr_class, mock_setup_logging, mock_load_config
    ):
        """Test main function when Bazarr API fails."""
        # Mock configuration loading to succeed
        mock_config = {
            "log_level": "INFO",
            "log_file": "test.log",
            "bazarr_url": "https://test.bazarr.com",
            "api_key": "test_key",
            "username": "test_user",
            "password": "test_pass",
        }
        mock_load_config.return_value = mock_config

        # Mock Bazarr client to return None (API failure)
        mock_bazarr = Mock()
        mock_bazarr.get_wanted_movies.return_value = None
        mock_bazarr_class.return_value = mock_bazarr

        # Mock logging
        mock_logger = Mock()
        with patch("run.logging.getLogger", return_value=mock_logger):
            with patch("run.sys.exit") as mock_exit:
                # When sys.exit is called, it should raise SystemExit, but
                # we're mocking it so the function continues and may hit
                # multiple sys.exit calls. Let's make sys.exit actually
                # exit to prevent multiple calls
                mock_exit.side_effect = SystemExit(1)
                with self.assertRaises(SystemExit):
                    run.main()
                mock_exit.assert_called_once_with(1)

    @patch("run.load_config")
    @patch("builtins.print")
    def test_main_config_error(self, mock_print, mock_load_config):
        """Test main function when configuration loading fails."""
        # Mock configuration loading to raise exception
        mock_load_config.side_effect = Exception("Config error")

        with patch("run.sys.exit") as mock_exit:
            run.main()
            mock_exit.assert_called_once_with(1)

    @patch("run.load_config")
    @patch("run.setup_logging")
    @patch("builtins.print")
    def test_main_keyboard_interrupt(
        self, mock_print, mock_setup_logging, mock_load_config
    ):
        """Test main function handles keyboard interrupt gracefully."""
        # Mock configuration
        mock_config = {"log_level": "INFO", "log_file": "test.log"}
        mock_load_config.return_value = mock_config

        # Mock setup_logging to raise KeyboardInterrupt
        mock_setup_logging.side_effect = KeyboardInterrupt()

        # Mock logging
        mock_logger = Mock()
        with patch("run.logging.getLogger", return_value=mock_logger):
            with patch("run.sys.exit") as mock_exit:
                run.main()
                mock_exit.assert_called_once_with(0)

    @patch("run.load_config")
    @patch("run.setup_logging")
    @patch("run.Bazarr")
    @patch("run.SubSourceDownloader")
    @patch("builtins.print")
    def test_main_no_radarr_id(
        self,
        mock_print,
        mock_downloader_class,
        mock_bazarr_class,
        mock_setup_logging,
        mock_load_config,
    ):
        """Test main function when movie has no Radarr ID."""
        # Mock configuration
        mock_config = {
            "log_level": "INFO",
            "log_file": "test.log",
            "bazarr_url": "https://test.bazarr.com",
            "api_key": "test_key",
            "username": "test_user",
            "password": "test_pass",
            "subsource_api_url": "https://api.test.com",
            "download_directory": "/tmp",
        }
        mock_load_config.return_value = mock_config

        # Mock movies data without radarrId
        movies_data = {
            "data": [
                {
                    "title": "Test Movie",
                    "missing_subtitles": [
                        {"name": "English", "code2": "en", "forced": False, "hi": False}
                    ],
                }
            ]
        }

        # Mock Bazarr client
        mock_bazarr = Mock()
        mock_bazarr.get_wanted_movies.return_value = movies_data
        mock_bazarr_class.return_value = mock_bazarr

        # Mock SubSource downloader
        mock_downloader = Mock()
        mock_downloader.get_subtitle_for_movie.return_value = (["/tmp/test.srt"], 0)
        mock_downloader_class.return_value = mock_downloader

        # Mock logging
        mock_logger = Mock()
        with patch("run.logging.getLogger", return_value=mock_logger):
            run.main()

        # Verify error message was printed
        print_calls = [call[0][0] for call in mock_print.call_args_list]
        self.assertIn("  ✗ No Radarr ID found, cannot upload to Bazarr", print_calls)

    @patch("run.load_config")
    @patch("run.setup_logging")
    @patch("run.Bazarr")
    @patch("run.SubSourceDownloader")
    @patch("builtins.print")
    def test_main_no_subtitles_downloaded(
        self,
        mock_print,
        mock_downloader_class,
        mock_bazarr_class,
        mock_setup_logging,
        mock_load_config,
    ):
        """Test main function when no subtitles are downloaded."""
        # Mock configuration
        mock_config = {
            "log_level": "INFO",
            "log_file": "test.log",
            "bazarr_url": "https://test.bazarr.com",
            "api_key": "test_key",
            "username": "test_user",
            "password": "test_pass",
            "subsource_api_url": "https://api.test.com",
            "download_directory": "/tmp",
        }
        mock_load_config.return_value = mock_config

        # Mock movies data
        movies_data = {
            "data": [
                {
                    "title": "Test Movie",
                    "radarrId": 123,
                    "missing_subtitles": [
                        {"name": "English", "code2": "en", "forced": False, "hi": False}
                    ],
                }
            ]
        }

        # Mock Bazarr client
        mock_bazarr = Mock()
        mock_bazarr.get_wanted_movies.return_value = movies_data
        mock_bazarr_class.return_value = mock_bazarr

        # Mock SubSource downloader to return no files
        mock_downloader = Mock()
        mock_downloader.get_subtitle_for_movie.return_value = ([], 1)
        mock_downloader_class.return_value = mock_downloader

        # Mock logging
        mock_logger = Mock()
        with patch("run.logging.getLogger", return_value=mock_logger):
            run.main()

        # Verify appropriate message was printed
        print_calls = [call[0][0] for call in mock_print.call_args_list]
        self.assertIn("  No subtitles downloaded for this movie.", print_calls)

        # Verify warning was logged
        mock_logger.warning.assert_called_with(
            "Execution completed with no successful uploads."
        )


if __name__ == "__main__":
    unittest.main()
