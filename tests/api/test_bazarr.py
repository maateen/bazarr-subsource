"""
Tests for api.bazarr module.
"""

import json
import unittest
from unittest.mock import Mock, patch

import requests

from api.bazarr import Bazarr


class TestBazarr(unittest.TestCase):
    """Test cases for Bazarr API client."""

    def setUp(self):
        """Set up test fixtures."""
        self.bazarr_url = "https://test.bazarr.com"
        self.api_key = "test_api_key"
        self.username = "test_user"
        self.password = "test_pass"

        self.client = Bazarr(
            self.bazarr_url, self.api_key, self.username, self.password
        )

    def test_init(self):
        """Test Bazarr client initialization."""
        self.assertEqual(self.client.bazarr_url, self.bazarr_url)
        self.assertEqual(self.client.api_key, self.api_key)
        self.assertEqual(self.client.username, self.username)
        self.assertEqual(self.client.password, self.password)

        # Check session headers
        self.assertIn("X-API-KEY", self.client.session.headers)
        self.assertEqual(self.client.session.headers["X-API-KEY"], self.api_key)

        # Check auth setup
        self.assertIsInstance(self.client.auth, requests.auth.HTTPBasicAuth)

    @patch("api.bazarr.requests.Session.get")
    def test_get_wanted_movies_success(self, mock_get):
        """Test successful get_wanted_movies request."""
        mock_response = Mock()
        mock_response.json.return_value = {
            "data": [{"title": "Test Movie", "missing_subtitles": []}]
        }
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response

        result = self.client.get_wanted_movies()

        self.assertIsNotNone(result)
        self.assertIn("data", result)
        mock_get.assert_called_once()

        # Check URL and parameters
        call_args = mock_get.call_args
        self.assertIn(
            "/api/movies/wanted", call_args[0][0]
        )  # First positional arg is URL
        self.assertEqual(call_args[1]["params"], {"start": 0, "length": -1})

    @patch("api.bazarr.requests.Session.get")
    def test_get_wanted_movies_with_parameters(self, mock_get):
        """Test get_wanted_movies with custom parameters."""
        mock_response = Mock()
        mock_response.json.return_value = {"data": []}
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response

        self.client.get_wanted_movies(start=10, length=50)

        call_args = mock_get.call_args
        self.assertEqual(call_args[1]["params"], {"start": 10, "length": 50})

    @patch("api.bazarr.requests.Session.get")
    def test_get_wanted_movies_request_exception(self, mock_get):
        """Test get_wanted_movies handles request exceptions."""
        mock_get.side_effect = requests.exceptions.RequestException("Network error")

        result = self.client.get_wanted_movies()

        self.assertIsNone(result)

    @patch("api.bazarr.requests.Session.get")
    def test_get_wanted_movies_json_decode_error(self, mock_get):
        """Test get_wanted_movies handles JSON decode errors."""
        mock_response = Mock()
        mock_response.raise_for_status.return_value = None
        mock_response.json.side_effect = json.JSONDecodeError("Invalid JSON", "", 0)
        mock_get.return_value = mock_response

        result = self.client.get_wanted_movies()

        self.assertIsNone(result)

    @patch("builtins.open", create=True)
    @patch("os.path.basename")
    @patch("api.bazarr.requests.Session.post")
    def test_upload_subtitle_success(self, mock_post, mock_basename, mock_open):
        """Test successful subtitle upload."""
        mock_response = Mock()
        mock_response.raise_for_status.return_value = None
        mock_post.return_value = mock_response
        mock_basename.return_value = "test.srt"
        mock_open.return_value.__enter__.return_value = Mock()

        result = self.client.upload_subtitle_to_bazarr(
            radarr_id=123,
            subtitle_file="/path/to/test.srt",
            language="en",
            forced=True,
            hi=False,
        )

        self.assertTrue(result)
        mock_post.assert_called_once()

        # Check the request data
        call_args = mock_post.call_args
        expected_data = {
            "radarrid": 123,
            "language": "en",
            "forced": "true",
            "hi": "false",
        }
        self.assertEqual(call_args[1]["data"], expected_data)

    @patch("builtins.open", create=True)
    @patch("os.path.basename")
    @patch("api.bazarr.requests.Session.post")
    def test_upload_subtitle_request_exception(
        self, mock_post, mock_basename, mock_open
    ):
        """Test subtitle upload handles request exceptions."""
        mock_post.side_effect = requests.exceptions.RequestException("Network error")
        mock_basename.return_value = "test.srt"
        mock_open.return_value.__enter__.return_value = Mock()

        result = self.client.upload_subtitle_to_bazarr(
            radarr_id=123, subtitle_file="/path/to/test.srt", language="en"
        )

        self.assertFalse(result)

    @patch("builtins.open", side_effect=IOError("File not found"))
    def test_upload_subtitle_file_error(self, mock_open):
        """Test subtitle upload handles file errors."""
        result = self.client.upload_subtitle_to_bazarr(
            radarr_id=123, subtitle_file="/invalid/path/test.srt", language="en"
        )

        self.assertFalse(result)

    @patch("api.bazarr.requests.Session.get")
    def test_get_system_tasks_success(self, mock_get):
        """Test successful get_system_tasks request."""
        mock_response = Mock()
        mock_response.json.return_value = {"tasks": []}
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response

        result = self.client.get_system_tasks()

        self.assertIsNotNone(result)
        mock_get.assert_called_once()

    @patch("api.bazarr.requests.Session.get")
    def test_get_system_tasks_exception(self, mock_get):
        """Test get_system_tasks handles exceptions."""
        mock_get.side_effect = requests.exceptions.RequestException("Network error")

        result = self.client.get_system_tasks()

        self.assertIsNone(result)

    @patch.object(Bazarr, "get_system_tasks")
    def test_get_missing_subtitles_search_interval_no_tasks(self, mock_get_tasks):
        """Test search interval when no tasks are returned."""
        mock_get_tasks.return_value = None

        interval = self.client.get_missing_subtitles_search_interval()

        self.assertEqual(interval, 24)  # Default value

    @patch.object(Bazarr, "get_system_tasks")
    def test_get_missing_subtitles_search_interval_with_task(self, mock_get_tasks):
        """Test search interval when matching task is found."""
        mock_get_tasks.return_value = [
            {"name": "Search for Missing Movies Subtitles", "interval": "12:00:00"}
        ]

        interval = self.client.get_missing_subtitles_search_interval()

        self.assertEqual(interval, 12)

    @patch.object(Bazarr, "get_system_tasks")
    def test_get_missing_subtitles_search_interval_dict_format(self, mock_get_tasks):
        """Test search interval with dict format response."""
        mock_get_tasks.return_value = {
            "data": [{"name": "Search for Missing Movies Subtitles", "interval": "6h"}]
        }

        interval = self.client.get_missing_subtitles_search_interval()

        self.assertEqual(interval, 6)

    def test_parse_interval_to_minutes_hours_format(self):
        """Test parsing HH:MM:SS format."""
        # Test hours:minutes format
        minutes = self.client._parse_interval_to_minutes("12:30")
        self.assertEqual(minutes, 12 * 60 + 30)

        # Test hours only
        minutes = self.client._parse_interval_to_minutes("6")
        self.assertEqual(minutes, 6 * 60)

    def test_parse_interval_to_minutes_suffixed_format(self):
        """Test parsing suffixed formats."""
        # Test hours suffix
        minutes = self.client._parse_interval_to_minutes("24h")
        self.assertEqual(minutes, 24 * 60)

        # Test minutes suffix
        minutes = self.client._parse_interval_to_minutes("90m")
        self.assertEqual(minutes, 90)

        # Test seconds suffix
        minutes = self.client._parse_interval_to_minutes("3600s")
        self.assertEqual(minutes, 60)

    def test_parse_interval_to_minutes_every_format(self):
        """Test parsing 'every' formats."""
        # Test every X hours
        minutes = self.client._parse_interval_to_minutes("every 6 hours")
        self.assertEqual(minutes, 6 * 60)

        # Test every X minutes
        minutes = self.client._parse_interval_to_minutes("every 30 minutes")
        self.assertEqual(minutes, 30)

        # Test every day
        minutes = self.client._parse_interval_to_minutes("every day")
        self.assertEqual(minutes, 24 * 60)

        # Test every weekday
        minutes = self.client._parse_interval_to_minutes("every monday")
        self.assertEqual(minutes, 168 * 60)

    def test_parse_interval_to_minutes_invalid_format(self):
        """Test parsing invalid format raises ValueError."""
        with self.assertRaises(ValueError):
            self.client._parse_interval_to_minutes("invalid format")


if __name__ == "__main__":
    unittest.main()
