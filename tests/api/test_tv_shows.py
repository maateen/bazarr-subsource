"""
Test cases for TV Show SubSource API client.
"""

import tempfile
import unittest
from unittest.mock import Mock, patch

from api.tv_shows import TVShowSubSourceDownloader


class TestTVShowSubSourceDownloader(unittest.TestCase):
    """Test cases for TV Show SubSource API client."""

    def setUp(self):
        """Set up test downloader."""
        with tempfile.TemporaryDirectory() as temp_dir:
            self.temp_dir = temp_dir
            self.downloader = TVShowSubSourceDownloader(
                "https://api.test.com", temp_dir
            )

    def test_generate_episode_search_queries(self):
        """Test generation of episode search queries."""
        episode = {
            "seriesTitle": "Breaking Bad",
            "title": "Pilot",
            "season": 1,
            "episode": 1,
            "sceneName": "Breaking.Bad.S01E01.1080p.BluRay.x264-REWARD",
        }

        queries = self.downloader._generate_episode_search_queries(episode)

        self.assertEqual(len(queries), 4)
        self.assertIn("Breaking Bad S01E01", queries)
        self.assertIn("Breaking Bad Pilot", queries)
        self.assertIn("Breaking Bad", queries)

    def test_generate_episode_search_queries_minimal(self):
        """Test query generation with minimal episode data."""
        episode = {"seriesTitle": "Test Show"}

        queries = self.downloader._generate_episode_search_queries(episode)

        self.assertEqual(queries, ["Test Show"])

    def test_extract_episode_info_s01e01_format(self):
        """Test episode info extraction from S01E01 format."""
        subtitle = {"release_info": "Breaking.Bad.S01E01.720p.BluRay.x264-REWARD"}

        season, episode = self.downloader._extract_episode_info_from_subtitle(subtitle)

        self.assertEqual(season, 1)
        self.assertEqual(episode, 1)

    def test_extract_episode_info_1x01_format(self):
        """Test episode info extraction from 1x01 format."""
        subtitle = {"release_info": "Breaking.Bad.1x01.720p.HDTV.x264-CTU"}

        season, episode = self.downloader._extract_episode_info_from_subtitle(subtitle)

        self.assertEqual(season, 1)
        self.assertEqual(episode, 1)

    def test_extract_episode_info_no_match(self):
        """Test episode info extraction when no pattern matches."""
        subtitle = {"release_info": "Breaking.Bad.Complete.Series.BluRay"}

        season, episode = self.downloader._extract_episode_info_from_subtitle(subtitle)

        self.assertIsNone(season)
        self.assertIsNone(episode)

    def test_is_subtitle_match_success(self):
        """Test subtitle matching success."""
        subtitle = {"release_info": "Breaking.Bad.S01E01.720p.BluRay.x264-REWARD"}
        episode = {"season": 1, "episode": 1}

        is_match = self.downloader._is_subtitle_match(subtitle, episode)

        self.assertTrue(is_match)

    def test_is_subtitle_match_failure(self):
        """Test subtitle matching failure."""
        subtitle = {"release_info": "Breaking.Bad.S01E02.720p.BluRay.x264-REWARD"}
        episode = {"season": 1, "episode": 1}

        is_match = self.downloader._is_subtitle_match(subtitle, episode)

        self.assertFalse(is_match)

    def test_is_subtitle_match_no_episode_info(self):
        """Test subtitle matching when episode has no season/episode."""
        subtitle = {"release_info": "Breaking.Bad.S01E01.720p.BluRay.x264-REWARD"}
        episode = {"title": "Pilot"}

        is_match = self.downloader._is_subtitle_match(subtitle, episode)

        self.assertFalse(is_match)

    @patch("api.tv_shows.requests.Session.post")
    @patch("api.tv_shows.requests.Session.get")
    @patch.object(TVShowSubSourceDownloader, "_get_search_interval_hours")
    def test_search_episode_subtitles_success(self, mock_interval, mock_get, mock_post):
        """Test successful episode subtitle search."""
        # Mock interval hours
        mock_interval.return_value = 24

        # Mock movie search response
        movie_search_response = Mock()
        movie_search_response.json.return_value = {
            "results": [
                {
                    "title": "Breaking Bad S01E01",
                    "link": "/subtitles/breaking-bad-s01e01-pilot",
                    "type": "movie",
                }
            ]
        }
        movie_search_response.raise_for_status.return_value = None
        mock_post.return_value = movie_search_response

        # Mock subtitle fetch response
        subtitle_response = Mock()
        subtitle_response.json.return_value = [
            {
                "id": "12345",
                "language": "English",
                "release_info": "Breaking.Bad.S01E01.720p.BluRay.x264-REWARD",
            }
        ]
        subtitle_response.raise_for_status.return_value = None
        mock_get.return_value = subtitle_response

        episode = {
            "seriesTitle": "Breaking Bad",
            "title": "Pilot",
            "season": 1,
            "episode": 1,
        }

        results = self.downloader.search_episode_subtitles(episode, "english")

        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["id"], "12345")
        # Source query could be any of the tried queries due to deduplication
        self.assertIn(
            results[0]["source_query"],
            ["Breaking Bad S01E01", "Breaking Bad Pilot", "Breaking Bad"],
        )

    @patch("api.tv_shows.requests.Session.post")
    @patch.object(TVShowSubSourceDownloader, "_get_search_interval_hours")
    def test_search_episode_subtitles_no_results(self, mock_interval, mock_post):
        """Test episode search with no results."""
        # Mock interval hours
        mock_interval.return_value = 24

        # Mock empty search response
        mock_response = Mock()
        mock_response.json.return_value = {"results": []}
        mock_response.raise_for_status.return_value = None
        mock_post.return_value = mock_response

        episode = {
            "seriesTitle": "Nonexistent Show",
            "season": 1,
            "episode": 1,
        }

        results = self.downloader.search_episode_subtitles(episode)

        self.assertEqual(len(results), 0)

    @patch.object(TVShowSubSourceDownloader, "search_episode_subtitles")
    @patch.object(TVShowSubSourceDownloader, "download_subtitle")
    @patch.object(TVShowSubSourceDownloader, "_get_search_interval_hours")
    def test_get_subtitle_for_episode(self, mock_interval, mock_download, mock_search):
        """Test getting subtitles for an episode."""
        # Mock interval hours
        mock_interval.return_value = 24

        # Mock search results
        mock_search.return_value = [
            {"id": "12345", "language": "English"},
        ]

        # Mock download
        mock_download.return_value = "/path/to/subtitle.srt"

        # Mock tracker to not skip searches
        with patch.object(
            self.downloader.tracker, "should_skip_search", return_value=False
        ):
            episode = {
                "seriesTitle": "Breaking Bad",
                "season": 1,
                "episode": 1,
                "missing_subtitles": [{"name": "English", "code2": "en"}],
            }

            downloaded_files, skipped_count = self.downloader.get_subtitle_for_episode(
                episode
            )

            self.assertEqual(len(downloaded_files), 1)
            self.assertEqual(skipped_count, 0)
            self.assertEqual(downloaded_files[0], "/path/to/subtitle.srt")

    @patch.object(TVShowSubSourceDownloader, "_get_search_interval_hours")
    def test_get_subtitle_for_episode_with_tracking_skip(self, mock_interval):
        """Test getting subtitles when tracking suggests skipping."""
        mock_interval.return_value = 24

        # Mock tracker to skip searches
        with patch.object(
            self.downloader.tracker, "should_skip_search", return_value=True
        ):
            episode = {
                "seriesTitle": "Breaking Bad",
                "season": 1,
                "episode": 1,
                "missing_subtitles": [{"name": "English", "code2": "en"}],
            }

            downloaded_files, skipped_count = self.downloader.get_subtitle_for_episode(
                episode
            )

            self.assertEqual(len(downloaded_files), 0)
            self.assertEqual(skipped_count, 1)

    @patch("api.subsource.SubSourceDownloader")
    def test_download_subtitle_delegates_to_movie_downloader(
        self, mock_movie_downloader_class
    ):
        """Test that download_subtitle delegates to movie downloader."""
        # Mock the movie downloader instance
        mock_instance = Mock()
        mock_instance.download_subtitle.return_value = "/path/to/downloaded.srt"
        mock_movie_downloader_class.return_value = mock_instance

        subtitle = {"id": "12345", "download_url": "http://test.com/sub.zip"}
        filename = "test.srt"

        result = self.downloader.download_subtitle(subtitle, filename)

        self.assertEqual(result, "/path/to/downloaded.srt")
        mock_instance.download_subtitle.assert_called_once_with(subtitle, filename)


if __name__ == "__main__":
    unittest.main()
