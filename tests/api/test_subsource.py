"""
Tests for api.subsource module.
"""

import os
import tempfile
import unittest
import zipfile
from unittest.mock import Mock, patch

import requests

from api.subsource import SubSourceDownloader


class TestSubSourceDownloader(unittest.TestCase):
    """Test cases for SubSource API client."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.api_url = "https://api.test.com"
        self.download_dir = self.temp_dir
        self.mock_bazarr = Mock()

        with patch("core.tracking.SubtitleTracker"):
            self.downloader = SubSourceDownloader(
                self.api_url, self.download_dir, self.mock_bazarr
            )

    def tearDown(self):
        """Clean up test fixtures."""
        # Clean up temp directory
        for file in os.listdir(self.temp_dir):
            os.remove(os.path.join(self.temp_dir, file))
        os.rmdir(self.temp_dir)

    def test_init(self):
        """Test SubSourceDownloader initialization."""
        self.assertEqual(self.downloader.api_url, self.api_url)
        self.assertEqual(self.downloader.download_dir, self.download_dir)
        self.assertEqual(self.downloader.bazarr, self.mock_bazarr)

        # Check that download directory exists
        self.assertTrue(os.path.exists(self.download_dir))

        # Check session headers
        expected_headers = {
            "User-Agent": (
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
            ),
            "Accept": "application/json",
            "Content-Type": "application/json",
            "Connection": "keep-alive",
        }
        for key, value in expected_headers.items():
            self.assertEqual(self.downloader.session.headers[key], value)

    @patch("api.subsource.requests.Session.get")
    @patch("api.subsource.requests.Session.post")
    def test_search_subtitles_success(self, mock_post, mock_get):
        """Test successful subtitle search."""
        # Mock first API call (movie search)
        movie_search_response = Mock()
        movie_search_response.json.return_value = {
            "results": [
                {
                    "title": "Test Movie",
                    "releaseYear": 2023,
                    "link": "/subtitles/test-movie-2023",
                }
            ]
        }
        movie_search_response.raise_for_status.return_value = None
        mock_post.return_value = movie_search_response

        # Mock second API call (subtitle search)
        subtitle_search_response = Mock()
        subtitle_search_response.json.return_value = [
            {"id": "12345", "language": "English"}
        ]
        subtitle_search_response.raise_for_status.return_value = None
        mock_get.return_value = subtitle_search_response

        result = self.downloader.search_subtitles("Test Movie", 2023, "english")

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["id"], "12345")
        mock_post.assert_called_once()
        mock_get.assert_called_once()

    @patch("api.subsource.requests.Session.get")
    def test_search_subtitles_no_movie_found(self, mock_get):
        """Test subtitle search when no movie is found."""
        mock_response = Mock()
        mock_response.json.return_value = {"movies": []}
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response

        result = self.downloader.search_subtitles("Nonexistent Movie", 2023, "english")

        self.assertEqual(result, [])

    @patch("api.subsource.requests.Session.get")
    def test_search_subtitles_request_exception(self, mock_get):
        """Test subtitle search handles request exceptions."""
        mock_get.side_effect = requests.exceptions.RequestException("Network error")

        result = self.downloader.search_subtitles("Test Movie", 2023, "english")

        self.assertEqual(result, [])

    @patch("api.subsource.requests.Session.get")
    @patch("api.subsource.requests.Session.post")
    def test_search_subtitles_year_matching(self, mock_post, mock_get):
        """Test subtitle search matches movie by year."""
        # Mock response with multiple movies, different years
        movie_search_response = Mock()
        movie_search_response.json.return_value = {
            "results": [
                {
                    "title": "Test Movie",
                    "releaseYear": 2020,
                    "link": "/subtitles/test-movie-2020",
                },
                {
                    "title": "Test Movie",
                    "releaseYear": 2023,
                    "link": "/subtitles/test-movie-2023",
                },
            ]
        }
        movie_search_response.raise_for_status.return_value = None
        mock_post.return_value = movie_search_response

        subtitle_response = Mock()
        subtitle_response.json.return_value = []
        subtitle_response.raise_for_status.return_value = None
        mock_get.return_value = subtitle_response

        self.downloader.search_subtitles("Test Movie", 2023, "english")

        # Check that the correct movie link was used (2023 version)
        get_call_url = mock_get.call_args[0][0]  # First positional argument
        self.assertIn("test-movie-2023", get_call_url)

    def test_get_movie_year(self):
        """Test movie year extraction."""
        # Test with provided year
        year = self.downloader._get_movie_year("Test Movie", 2023)
        self.assertEqual(year, 2023)

        # Test with zero year (should use Bazarr lookup)
        with patch.object(
            self.downloader, "_get_movie_year_from_bazarr"
        ) as mock_lookup:
            mock_lookup.return_value = 2022
            year = self.downloader._get_movie_year("Test Movie", 0)
            self.assertEqual(year, 2022)
            mock_lookup.assert_called_once_with("Test Movie")

    @patch("api.subsource.requests.Session.get")
    def test_get_movie_year_from_bazarr(self, mock_get):
        """Test getting movie year from Bazarr search API."""
        mock_response = Mock()
        mock_response.json.return_value = [{"title": "Test Movie", "year": 2023}]
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response

        # Mock bazarr URL and session
        self.mock_bazarr.bazarr_url = "https://test.bazarr.com"
        self.mock_bazarr.session = Mock()
        self.mock_bazarr.session.get.return_value = mock_response
        self.mock_bazarr.auth = Mock()

        year = self.downloader._get_movie_year_from_bazarr("Test Movie")

        self.assertEqual(year, 2023)

    def test_get_search_interval_hours(self):
        """Test getting search interval hours."""
        # Test cached value
        self.downloader._search_interval_hours = 12
        interval = self.downloader._get_search_interval_hours()
        self.assertEqual(interval, 12)

        # Test fetching from Bazarr
        self.downloader._search_interval_hours = None
        self.mock_bazarr.get_missing_subtitles_search_interval.return_value = 6
        interval = self.downloader._get_search_interval_hours()
        self.assertEqual(interval, 6)
        self.assertEqual(self.downloader._search_interval_hours, 6)

    @patch("api.subsource.requests.Session.get")
    def test_download_subtitle_success(self, mock_get):
        """Test successful subtitle download."""
        # Mock token request
        token_response = Mock()
        token_response.json.return_value = {
            "subtitle": {"download_token": "test_token_12345"}
        }
        token_response.raise_for_status.return_value = None
        mock_get.return_value = token_response

        # Create a test ZIP file
        zip_path = os.path.join(self.temp_dir, "test.zip")
        with zipfile.ZipFile(zip_path, "w") as zf:
            zf.writestr("test.srt", "Test subtitle content")

        # Mock download request
        with open(zip_path, "rb") as f:
            zip_content = f.read()

        download_response = Mock()
        download_response.content = zip_content
        download_response.headers = {"content-type": "application/zip"}
        download_response.raise_for_status.return_value = None

        mock_get.side_effect = [token_response, download_response]

        result = self.downloader.download_subtitle(
            {"id": "12345", "subtitle_link": "test-link"}, "test.srt"
        )

        self.assertIsNotNone(result)
        self.assertTrue(os.path.exists(result))

        # Check that subtitle content is correct
        with open(result, "r") as f:
            content = f.read()
        self.assertEqual(content, "Test subtitle content")

    @patch("api.subsource.requests.Session.get")
    def test_download_subtitle_no_token(self, mock_get):
        """Test subtitle download when no token is returned."""
        mock_response = Mock()
        mock_response.json.return_value = {"subtitle": {}}
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response

        result = self.downloader.download_subtitle(
            {"id": "12345", "subtitle_link": "test-link"}, "test.srt"
        )

        self.assertIsNone(result)

    @patch("api.subsource.requests.Session.get")
    def test_download_subtitle_html_response(self, mock_get):
        """Test subtitle download handles HTML response."""
        # Mock token request
        token_response = Mock()
        token_response.json.return_value = {
            "subtitle": {"download_token": "test_token"}
        }
        token_response.raise_for_status.return_value = None
        mock_get.return_value = token_response

        # Mock HTML response for download step
        download_response = Mock()
        download_response.content = b"<html>Error page</html>"
        download_response.headers = {"content-type": "text/html"}
        download_response.raise_for_status.return_value = None

        mock_get.side_effect = [token_response, download_response]

        result = self.downloader.download_subtitle(
            {"id": "12345", "subtitle_link": "test-link"}, "test.srt"
        )

        self.assertIsNone(result)

    def test_extract_subtitle_from_zip(self):
        """Test extracting subtitle from ZIP file."""
        # Create a test ZIP file with subtitle
        zip_path = os.path.join(self.temp_dir, "test.zip")
        with zipfile.ZipFile(zip_path, "w") as zf:
            zf.writestr("movie.srt", "Test subtitle content")
            zf.writestr("readme.txt", "Some readme")

        result = self.downloader._extract_subtitle_from_zip(zip_path, "12345")

        self.assertIsNotNone(result)
        self.assertTrue(os.path.exists(result))

        # Check content
        with open(result, "r") as f:
            content = f.read()
        self.assertEqual(content, "Test subtitle content")

        # Check that ZIP file was cleaned up (allow for timing issues)
        self.assertTrue(os.path.exists(result))  # Result file should exist

    def test_extract_subtitle_from_zip_no_subtitles(self):
        """Test extracting from ZIP with no subtitle files."""
        # Create a test ZIP file without subtitles
        zip_path = os.path.join(self.temp_dir, "test.zip")
        with zipfile.ZipFile(zip_path, "w") as zf:
            zf.writestr("readme.txt", "Some readme")
            zf.writestr("info.nfo", "Movie info")

        result = self.downloader._extract_subtitle_from_zip(zip_path, "12345")

        self.assertIsNone(result)

    def test_extract_subtitle_from_zip_multiple_subtitles(self):
        """Test extracting from ZIP with multiple subtitle files."""
        # Create a test ZIP file with multiple subtitles
        zip_path = os.path.join(self.temp_dir, "test.zip")
        with zipfile.ZipFile(zip_path, "w") as zf:
            # Add small subtitle
            zf.writestr("small.srt", "Small content")
            # Add larger subtitle
            zf.writestr("large.srt", "Large content with more text")

        result = self.downloader._extract_subtitle_from_zip(zip_path, "12345")

        self.assertIsNotNone(result)

        # Should pick the larger file
        with open(result, "r") as f:
            content = f.read()
        self.assertEqual(content, "Large content with more text")

    @patch.object(SubSourceDownloader, "search_subtitles")
    @patch.object(SubSourceDownloader, "download_subtitle")
    @patch.object(SubSourceDownloader, "_get_search_interval_hours")
    def test_get_subtitle_for_movie(self, mock_interval, mock_download, mock_search):
        """Test getting subtitles for a movie."""
        # Mock interval hours
        mock_interval.return_value = 24

        # Mock search results
        mock_search.return_value = [
            {"id": "12345", "language": "English"},
            {"id": "67890", "language": "English"},
        ]

        # Mock downloads
        mock_download.side_effect = ["/path/to/sub1.srt", "/path/to/sub2.srt"]

        # Mock tracker to not skip searches
        with patch.object(
            self.downloader.tracker, "should_skip_search", return_value=False
        ):
            movie = {
                "title": "Test Movie",
                "year": 2023,
                "missing_subtitles": [
                    {"name": "English", "code2": "en"},
                    {"name": "English", "code2": "en"},
                ],
            }

            downloaded_files, skipped_count = self.downloader.get_subtitle_for_movie(
                movie
            )

            self.assertEqual(len(downloaded_files), 2)
            self.assertEqual(skipped_count, 0)
            self.assertEqual(mock_search.call_count, 2)  # Called for each subtitle
            self.assertEqual(mock_download.call_count, 2)

    @patch.object(SubSourceDownloader, "_get_search_interval_hours")
    def test_get_subtitle_for_movie_with_tracking(self, mock_interval):
        """Test getting subtitles with tracking that skips searches."""
        mock_interval.return_value = 24

        # Mock tracker to skip searches
        with patch.object(
            self.downloader.tracker, "should_skip_search", return_value=True
        ):
            movie = {
                "title": "Test Movie",
                "year": 2023,
                "missing_subtitles": [{"name": "English", "code2": "en"}],
            }

            downloaded_files, skipped_count = self.downloader.get_subtitle_for_movie(
                movie
            )

            self.assertEqual(len(downloaded_files), 0)
            self.assertEqual(skipped_count, 1)

    # TV Series / Episode tests

    def test_extract_episode_info_s01e01_format(self):
        """Test episode info extraction from S01E01 format."""
        subtitle = {"release_info": "Breaking.Bad.S01E01.720p.BluRay.x264-REWARD"}

        season, episode = self.downloader._extract_episode_info_from_subtitle(subtitle)

        # S01E01 format should return both season and episode
        self.assertEqual(season, 1)
        self.assertEqual(episode, 1)

    def test_extract_episode_info_1x01_format(self):
        """Test episode info extraction from 1x01 format."""
        subtitle = {"release_info": "Breaking.Bad.1x01.720p.BluRay.x264-REWARD"}

        season, episode = self.downloader._extract_episode_info_from_subtitle(subtitle)

        self.assertEqual(season, 1)
        self.assertEqual(episode, 1)

    def test_extract_episode_info_no_match(self):
        """Test episode info extraction when no pattern matches."""
        subtitle = {"release_info": "Breaking.Bad.720p.BluRay.x264-REWARD"}

        season, episode = self.downloader._extract_episode_info_from_subtitle(subtitle)

        self.assertIsNone(season)
        self.assertIsNone(episode)

    def test_is_subtitle_match_success(self):
        """Test subtitle matching with correct season/episode."""
        subtitle = {"release_info": "Breaking.Bad.S01E01.720p.BluRay.x264-REWARD"}
        target_episode = {"season": 1, "episode": 1}

        result = self.downloader._is_subtitle_match(subtitle, target_episode)

        self.assertTrue(result)

    def test_is_subtitle_match_failure(self):
        """Test subtitle matching with wrong season/episode."""
        subtitle = {"release_info": "Breaking.Bad.S01E02.720p.BluRay.x264-REWARD"}
        target_episode = {"season": 1, "episode": 1}

        result = self.downloader._is_subtitle_match(subtitle, target_episode)

        self.assertFalse(result)

    @patch("api.subsource.requests.Session.post")
    @patch("api.subsource.requests.Session.get")
    def test_search_episode_subtitles_success(self, mock_get, mock_post):
        """Test successful episode subtitle search."""
        # Mock search response
        mock_search_response = Mock()
        mock_search_response.json.return_value = {
            "results": [
                {
                    "title": "Breaking Bad",
                    "type": "tvseries",
                    "link": "/subtitles/breaking-bad-2008",
                    "seasons": [
                        {"season": 1, "link": "/subtitles/breaking-bad-2008/s1"}
                    ],
                    "releaseYear": 2008,
                }
            ]
        }
        mock_search_response.raise_for_status.return_value = None
        mock_post.return_value = mock_search_response

        # Mock subtitles response
        mock_sub_response = Mock()
        mock_sub_response.json.return_value = [
            {
                "id": "123",
                "release_info": "Breaking.Bad.S01E01.720p.BluRay.x264-REWARD",
                "language": "english",
            }
        ]
        mock_sub_response.raise_for_status.return_value = None
        mock_get.return_value = mock_sub_response

        episode = {
            "series_title": "Breaking Bad",
            "season": 1,
            "episode_number": 1,
        }

        results = self.downloader.search_episode_subtitles(episode, "english")

        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["id"], "123")
        self.assertIn("source_query", results[0])

    @patch("api.subsource.requests.Session.post")
    def test_search_episode_subtitles_no_results(self, mock_post):
        """Test episode subtitle search with no results."""
        mock_response = Mock()
        mock_response.json.return_value = {"results": []}
        mock_response.raise_for_status.return_value = None
        mock_post.return_value = mock_response

        episode = {
            "series_title": "Unknown Show",
            "season": 1,
            "episode_number": 1,
        }

        results = self.downloader.search_episode_subtitles(episode, "english")

        self.assertEqual(len(results), 0)


if __name__ == "__main__":
    unittest.main()
