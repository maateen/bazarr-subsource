"""
Test cases for Bazarr Episode API client.
"""

import os
import tempfile
import unittest
from unittest.mock import Mock, patch

from api.bazarr_episodes import BazarrEpisodeClient


class TestBazarrEpisodeClient(unittest.TestCase):
    """Test cases for Bazarr Episode API client."""

    def setUp(self):
        """Set up test client."""
        self.client = BazarrEpisodeClient(
            "http://localhost:6767", "test-api-key", "testuser", "testpass"
        )

    @patch("api.bazarr_episodes.requests.Session.get")
    def test_get_wanted_episodes_success(self, mock_get):
        """Test successful retrieval of wanted episodes."""
        # Mock response data
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
                    "sceneName": "Breaking.Bad.S01E01.1080p.BluRay.x264-REWARD",
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

    @patch("api.bazarr_episodes.requests.Session.get")
    def test_get_wanted_episodes_empty(self, mock_get):
        """Test retrieval when no episodes want subtitles."""
        mock_response = Mock()
        mock_response.json.return_value = {"data": []}
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response

        episodes = self.client.get_wanted_episodes()

        self.assertEqual(len(episodes), 0)

    @patch("api.bazarr_episodes.requests.Session.get")
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

    @patch("api.bazarr_episodes.requests.Session.get")
    def test_get_series_info_not_found(self, mock_get):
        """Test series info when series not found."""
        mock_response = Mock()
        mock_response.json.return_value = {"data": []}
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response

        series_info = self.client.get_series_info(999)

        self.assertIsNone(series_info)

    def test_enrich_episode_data_success(self):
        """Test episode data enrichment."""
        episode = {
            "sonarrEpisodeId": 123,
            "sonarrSeriesId": 456,
            "title": "Pilot",
        }

        with patch.object(self.client, "get_series_info") as mock_get_series:
            mock_get_series.return_value = {
                "title": "Breaking Bad",
                "year": 2008,
                "imdbId": "tt0903747",
            }

            enriched = self.client._enrich_episode_data(episode)

            self.assertEqual(enriched["seriesTitle"], "Breaking Bad")
            self.assertEqual(enriched["seriesYear"], 2008)
            self.assertEqual(enriched["seriesImdb"], "tt0903747")

    def test_enrich_episode_data_no_series_id(self):
        """Test episode enrichment when no series ID."""
        episode = {
            "sonarrEpisodeId": 123,
            "title": "Pilot",
        }

        enriched = self.client._enrich_episode_data(episode)

        # Should return original episode
        self.assertEqual(enriched, episode)

    @patch("api.bazarr_episodes.requests.Session.post")
    def test_upload_episode_subtitle_success(self, mock_post):
        """Test successful episode subtitle upload."""
        mock_response = Mock()
        mock_response.raise_for_status.return_value = None
        mock_post.return_value = mock_response

        # Create temporary subtitle file
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
            self.assertIn("seriesid", call_args[1]["params"])
            self.assertEqual(call_args[1]["params"]["seriesid"], 456)
            self.assertEqual(call_args[1]["params"]["episodeid"], 123)
            self.assertEqual(call_args[1]["params"]["language"], "en")

        finally:
            os.unlink(temp_file)

    def test_upload_episode_subtitle_file_not_found(self):
        """Test subtitle upload with non-existent file."""
        result = self.client.upload_episode_subtitle(
            series_id=456,
            episode_id=123,
            language="en",
            subtitle_file="/non/existent/file.srt",
        )

        self.assertFalse(result)

    @patch("api.bazarr_episodes.requests.Session.get")
    def test_get_search_interval_success(self, mock_get):
        """Test getting search interval from Bazarr."""
        mock_response = Mock()
        mock_response.json.return_value = {"general": {"episode_search_interval": 12}}
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response

        interval = self.client.get_search_interval()

        self.assertEqual(interval, 12)

    @patch("api.bazarr_episodes.requests.Session.get")
    def test_get_search_interval_fallback(self, mock_get):
        """Test search interval fallback when API fails."""
        mock_get.side_effect = Exception("API Error")

        interval = self.client.get_search_interval()

        self.assertEqual(interval, 24)  # Default fallback


if __name__ == "__main__":
    unittest.main()
