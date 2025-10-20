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

        result = self.client.upload_movie_subtitle(
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

        result = self.client.upload_movie_subtitle(
            radarr_id=123, subtitle_file="/path/to/test.srt", language="en"
        )

        self.assertFalse(result)

    @patch("builtins.open", side_effect=IOError("File not found"))
    def test_upload_subtitle_file_error(self, mock_open):
        """Test subtitle upload handles file errors."""
        result = self.client.upload_movie_subtitle(
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

    @patch("api.bazarr.requests.Session.patch")
    def test_sync_subtitle_success(self, mock_patch):
        """Test successful subtitle synchronization."""
        mock_response = Mock()
        mock_response.raise_for_status.return_value = None
        mock_patch.return_value = mock_response

        result = self.client.sync_subtitle(
            subtitle_path="/path/to/subtitle.srt",
            media_type="movie",
            media_id=123,
            language="en",
            forced=False,
            hi=False,
        )

        self.assertTrue(result)
        mock_patch.assert_called_once()

        # Check the call parameters
        call_args = mock_patch.call_args
        self.assertIn("params", call_args.kwargs)
        params = call_args.kwargs["params"]
        self.assertEqual(params["action"], "sync")
        self.assertEqual(params["language"], "en")
        self.assertEqual(params["path"], "/path/to/subtitle.srt")
        self.assertEqual(params["type"], "movie")
        self.assertEqual(params["id"], 123)

    @patch("api.bazarr.requests.Session.patch")
    def test_sync_subtitle_with_options(self, mock_patch):
        """Test subtitle synchronization with custom options."""
        mock_response = Mock()
        mock_response.raise_for_status.return_value = None
        mock_patch.return_value = mock_response

        result = self.client.sync_subtitle(
            subtitle_path="/path/to/subtitle.srt",
            media_type="episode",
            media_id=456,
            language="fr",
            forced=True,
            hi=True,
            reference="a:1",
            max_offset_seconds=600,
            no_fix_framerate=True,
            use_gss=True,
        )

        self.assertTrue(result)

        # Check custom parameters
        call_args = mock_patch.call_args
        params = call_args.kwargs["params"]
        self.assertEqual(params["forced"], "true")
        self.assertEqual(params["hi"], "true")
        self.assertEqual(params["reference"], "a:1")
        self.assertEqual(params["max_offset_seconds"], "600")
        self.assertEqual(params["no_fix_framerate"], "true")
        self.assertEqual(params["gss"], "true")

    @patch("api.bazarr.requests.Session.patch")
    def test_sync_subtitle_exception(self, mock_patch):
        """Test sync_subtitle handles exceptions."""
        mock_patch.side_effect = requests.exceptions.RequestException("Network error")

        result = self.client.sync_subtitle(
            subtitle_path="/path/to/subtitle.srt",
            media_type="movie",
            media_id=123,
            language="en",
        )

        self.assertFalse(result)

    @patch("api.bazarr.requests.Session.get")
    def test_get_movie_subtitles_success(self, mock_get):
        """Test successful get_movie_subtitles request."""
        mock_response = Mock()
        mock_response.json.return_value = {
            "data": [
                {
                    "radarrid": 123,
                    "title": "Test Movie",
                    "subtitles": [
                        {
                            "code2": "en",
                            "path": "/path/to/subtitle.srt",
                            "forced": False,
                            "hi": False,
                        }
                    ],
                }
            ]
        }
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response

        result = self.client.get_movie_subtitles(123)

        self.assertIsNotNone(result)
        self.assertEqual(result["radarrid"], 123)
        self.assertIn("subtitles", result)
        mock_get.assert_called_once()

    @patch("api.bazarr.requests.Session.get")
    def test_get_movie_subtitles_exception(self, mock_get):
        """Test get_movie_subtitles handles exceptions."""
        mock_get.side_effect = requests.exceptions.RequestException("Network error")

        result = self.client.get_movie_subtitles(123)

        self.assertIsNone(result)

    # Episode-related tests

    @patch("api.bazarr.requests.Session.get")
    def test_get_wanted_episodes_success(self, mock_get):
        """Test successful retrieval of wanted episodes."""
        mock_response = Mock()
        mock_response.json.return_value = {
            "data": [
                {
                    "sonarrEpisodeId": 123,
                    "sonarrSeriesId": 456,
                    "title": "Pilot",
                    "season": 1,
                    "episode": 1,
                    "missing_subtitles": [{"name": "English", "code2": "en"}],
                },
                {
                    "sonarrEpisodeId": 124,
                    "sonarrSeriesId": 456,
                    "title": "Cat's in the Bag",
                    "season": 1,
                    "episode": 2,
                    "missing_subtitles": [{"name": "Spanish", "code2": "es"}],
                },
            ]
        }
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response

        # Mock series enrichment
        with patch.object(self.client, "_enrich_episode_data", side_effect=lambda x: x):
            episodes = self.client.get_wanted_episodes()

        self.assertEqual(len(episodes), 2)
        self.assertEqual(episodes[0]["title"], "Pilot")
        self.assertEqual(episodes[0]["season"], 1)
        self.assertEqual(episodes[0]["episode"], 1)
        mock_get.assert_called_once()

    @patch("api.bazarr.requests.Session.get")
    def test_get_series_info_success(self, mock_get):
        """Test successful series info retrieval."""
        mock_response = Mock()
        mock_response.json.return_value = {
            "data": [
                {
                    "sonarrSeriesId": 456,
                    "title": "Breaking Bad",
                    "year": 2008,
                    "imdbId": "tt0903747",
                }
            ]
        }
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response

        series_info = self.client.get_series_info(456)

        self.assertIsNotNone(series_info)
        self.assertEqual(series_info["title"], "Breaking Bad")
        self.assertEqual(series_info["year"], 2008)

    @patch("api.bazarr.requests.Session.post")
    def test_upload_episode_subtitle_success(self, mock_post):
        """Test successful episode subtitle upload."""
        mock_response = Mock()
        mock_response.raise_for_status.return_value = None
        mock_post.return_value = mock_response

        # Create temporary subtitle file
        import tempfile

        with tempfile.NamedTemporaryFile(mode="w", suffix=".srt", delete=False) as f:
            f.write("1\n00:00:01,000 --> 00:00:02,000\nTest subtitle\n")
            temp_file = f.name

        try:
            result = self.client.upload_episode_subtitle(
                series_id=456,
                episode_id=123,
                language="en",
                subtitle_file=temp_file,
                forced=False,
                hi=False,
            )

            self.assertTrue(result)
            mock_post.assert_called_once()

            # Check call parameters
            call_args = mock_post.call_args
            self.assertIn("params", call_args.kwargs)
            self.assertEqual(call_args.kwargs["params"]["seriesid"], 456)
            self.assertEqual(call_args.kwargs["params"]["episodeid"], 123)
            self.assertEqual(call_args.kwargs["params"]["language"], "en")

        finally:
            import os

            os.unlink(temp_file)

    @patch("api.bazarr.requests.Session.patch")
    def test_sync_episode_subtitle_success(self, mock_patch):
        """Test successful episode subtitle synchronization."""
        mock_response = Mock()
        mock_response.raise_for_status.return_value = None
        mock_patch.return_value = mock_response

        result = self.client.sync_episode_subtitle(
            subtitle_path="/path/to/episode.srt",
            series_id=456,
            episode_id=123,
            language="en",
            forced=False,
            hi=False,
        )

        self.assertTrue(result)
        mock_patch.assert_called_once()

        # Check the call parameters
        call_args = mock_patch.call_args
        self.assertIn("params", call_args.kwargs)
        params = call_args.kwargs["params"]
        self.assertEqual(params["action"], "sync")
        self.assertEqual(params["language"], "en")
        self.assertEqual(params["path"], "/path/to/episode.srt")
        self.assertEqual(params["type"], "episode")
        self.assertEqual(params["id"], 123)

    @patch("api.bazarr.requests.Session.get")
    def test_get_episode_subtitles_success(self, mock_get):
        """Test successful get_episode_subtitles request."""
        mock_response = Mock()
        mock_response.json.return_value = {
            "data": [
                {
                    "sonarrEpisodeId": 123,
                    "title": "Test Episode",
                    "subtitles": [
                        {
                            "code2": "en",
                            "path": "/path/to/episode.srt",
                            "forced": False,
                            "hi": False,
                        }
                    ],
                }
            ]
        }
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response

        result = self.client.get_episode_subtitles(456, 123)

        self.assertIsNotNone(result)
        self.assertEqual(result["sonarrEpisodeId"], 123)
        self.assertIn("subtitles", result)
        mock_get.assert_called_once()

    @patch("api.bazarr.requests.Session.get")
    def test_get_system_settings_success(self, mock_get):
        """Test successful get_system_settings request."""
        mock_response = Mock()
        mock_response.json.return_value = {
            "subsync": {
                "max_offset_seconds": 300,
                "no_fix_framerate": True,
                "gss": False,
            },
            "general": {"use_subsync": True},
        }
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response

        result = self.client.get_system_settings()

        self.assertIsNotNone(result)
        self.assertIn("subsync", result)
        mock_get.assert_called_once()

    @patch("api.bazarr.requests.Session.get")
    def test_get_system_settings_exception(self, mock_get):
        """Test get_system_settings handles exceptions."""
        mock_get.side_effect = requests.exceptions.RequestException("Network error")

        result = self.client.get_system_settings()

        self.assertIsNone(result)

    @patch.object(Bazarr, "get_system_settings")
    def test_get_sync_settings_success(self, mock_get_settings):
        """Test successful sync settings retrieval."""
        mock_get_settings.return_value = {
            "subsync": {
                "use_subsync": False,
                "max_offset_seconds": 600,
                "no_fix_framerate": True,
                "gss": True,
            }
        }

        result = self.client.get_sync_settings()

        expected = {
            "enabled": False,
            "max_offset_seconds": 600,
            "no_fix_framerate": True,
            "use_gss": True,
            "reference": "a:0",
        }
        self.assertEqual(result, expected)

    @patch.object(Bazarr, "get_system_settings")
    def test_get_sync_settings_no_subsync_section(self, mock_get_settings):
        """Test sync settings with missing subsync section."""
        mock_get_settings.return_value = {"general": {"some_setting": True}}

        result = self.client.get_sync_settings()

        expected = {
            "enabled": False,
            "max_offset_seconds": 300,
            "no_fix_framerate": False,
            "use_gss": False,
            "reference": "a:0",
        }
        self.assertEqual(result, expected)

    @patch.object(Bazarr, "get_system_settings")
    def test_get_sync_settings_api_failure(self, mock_get_settings):
        """Test sync settings when API call fails."""
        mock_get_settings.return_value = None

        result = self.client.get_sync_settings()

        expected = {
            "enabled": False,
            "max_offset_seconds": 300,
            "no_fix_framerate": False,
            "use_gss": False,
            "reference": "a:0",
        }
        self.assertEqual(result, expected)

    @patch.object(Bazarr, "get_system_settings")
    def test_get_sync_settings_enabled(self, mock_get_settings):
        """Test sync settings when SubSync is enabled."""
        mock_get_settings.return_value = {
            "subsync": {
                "use_subsync": True,
                "max_offset_seconds": 600,
                "no_fix_framerate": False,
                "gss": True,
            }
        }

        result = self.client.get_sync_settings()

        expected = {
            "enabled": True,
            "max_offset_seconds": 600,
            "no_fix_framerate": False,
            "use_gss": True,
            "reference": "a:0",
        }
        self.assertEqual(result, expected)

    @patch.object(Bazarr, "get_system_settings")
    def test_get_subzero_settings_enabled(self, mock_get_settings):
        """Test Sub-Zero settings when modifications are enabled."""
        mock_get_settings.return_value = {
            "general": {"subzero_mods": ["common", "hearing_impaired"]}
        }

        result = self.client.get_subzero_settings()

        expected = {"mods": ["common", "hearing_impaired"], "enabled": True}
        self.assertEqual(result, expected)

    @patch.object(Bazarr, "get_system_settings")
    def test_get_subzero_settings_disabled(self, mock_get_settings):
        """Test Sub-Zero settings when no modifications are configured."""
        mock_get_settings.return_value = {"general": {"subzero_mods": []}}

        result = self.client.get_subzero_settings()

        expected = {"mods": [], "enabled": False}
        self.assertEqual(result, expected)

    @patch.object(Bazarr, "get_system_settings")
    def test_get_subzero_settings_missing_section(self, mock_get_settings):
        """Test Sub-Zero settings when general section is missing."""
        mock_get_settings.return_value = {"subsync": {"use_subsync": True}}

        result = self.client.get_subzero_settings()

        expected = {"mods": [], "enabled": False}
        self.assertEqual(result, expected)

    @patch.object(Bazarr, "get_system_settings")
    def test_get_subzero_settings_api_failure(self, mock_get_settings):
        """Test Sub-Zero settings when API call fails."""
        mock_get_settings.return_value = None

        result = self.client.get_subzero_settings()

        expected = {"mods": [], "enabled": False}
        self.assertEqual(result, expected)

    @patch("api.bazarr.requests.Session.patch")
    def test_trigger_subzero_mods_success(self, mock_patch):
        """Test successful Sub-Zero modification trigger."""
        mock_response = Mock()
        mock_response.raise_for_status.return_value = None
        mock_patch.return_value = mock_response

        result = self.client.trigger_subzero_mods(
            subtitle_path="/path/to/subtitle.srt",
            media_type="movie",
            media_id=123,
            language="en",
            forced=False,
            hi=False,
        )

        self.assertTrue(result)
        mock_patch.assert_called_once()

        # Check the call parameters
        call_args = mock_patch.call_args
        self.assertIn("params", call_args.kwargs)
        params = call_args.kwargs["params"]
        self.assertEqual(params["action"], "subzero")
        self.assertEqual(params["language"], "en")
        self.assertEqual(params["path"], "/path/to/subtitle.srt")
        self.assertEqual(params["type"], "movie")
        self.assertEqual(params["id"], 123)

    @patch("api.bazarr.requests.Session.patch")
    def test_trigger_subzero_mods_exception(self, mock_patch):
        """Test Sub-Zero trigger handles exceptions."""
        mock_patch.side_effect = requests.exceptions.RequestException("Network error")

        result = self.client.trigger_subzero_mods(
            subtitle_path="/path/to/subtitle.srt",
            media_type="movie",
            media_id=123,
            language="en",
        )

        self.assertFalse(result)

    @patch("api.bazarr.requests.Session.patch")
    def test_trigger_episode_subzero_mods_success(self, mock_patch):
        """Test successful episode Sub-Zero modification trigger."""
        mock_response = Mock()
        mock_response.raise_for_status.return_value = None
        mock_patch.return_value = mock_response

        result = self.client.trigger_episode_subzero_mods(
            subtitle_path="/path/to/episode.srt",
            series_id=456,
            episode_id=123,
            language="fr",
            forced=True,
            hi=True,
        )

        self.assertTrue(result)
        mock_patch.assert_called_once()

        # Check the call parameters
        call_args = mock_patch.call_args
        self.assertIn("params", call_args.kwargs)
        params = call_args.kwargs["params"]
        self.assertEqual(params["action"], "subzero")
        self.assertEqual(params["language"], "fr")
        self.assertEqual(params["path"], "/path/to/episode.srt")
        self.assertEqual(params["type"], "episode")
        self.assertEqual(params["id"], 123)
        self.assertEqual(params["forced"], "true")
        self.assertEqual(params["hi"], "true")

    @patch("api.bazarr.requests.Session.patch")
    def test_trigger_episode_subzero_mods_exception(self, mock_patch):
        """Test episode Sub-Zero trigger handles exceptions."""
        mock_patch.side_effect = requests.exceptions.RequestException("Network error")

        result = self.client.trigger_episode_subzero_mods(
            subtitle_path="/path/to/episode.srt",
            series_id=456,
            episode_id=123,
            language="en",
        )

        self.assertFalse(result)


if __name__ == "__main__":
    unittest.main()
