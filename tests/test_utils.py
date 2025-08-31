"""
Tests for utils module.
"""

import unittest

from utils import format_movie_info


class TestUtils(unittest.TestCase):
    """Test cases for utility functions."""

    def test_format_movie_info_basic(self):
        """Test basic movie info formatting."""
        movie = {
            "title": "Test Movie",
            "year": 2023,
            "missing_subtitles": [{"name": "English", "forced": False, "hi": False}],
        }

        result = format_movie_info(movie)
        expected = "• Test Movie (2023) - Missing: English"

        self.assertEqual(result, expected)

    def test_format_movie_info_no_year(self):
        """Test movie info formatting without year."""
        movie = {
            "title": "Test Movie",
            "missing_subtitles": [{"name": "English", "forced": False, "hi": False}],
        }

        result = format_movie_info(movie)
        expected = "• Test Movie - Missing: English"

        self.assertEqual(result, expected)

    def test_format_movie_info_alternative_year_fields(self):
        """Test movie info formatting with alternative year field names."""
        # Test movie_year field
        movie = {
            "title": "Test Movie",
            "movie_year": 2023,
            "missing_subtitles": [{"name": "English", "forced": False, "hi": False}],
        }

        result = format_movie_info(movie)
        expected = "• Test Movie (2023) - Missing: English"
        self.assertEqual(result, expected)

        # Test releaseYear field
        movie = {
            "title": "Test Movie",
            "releaseYear": 2023,
            "missing_subtitles": [{"name": "English", "forced": False, "hi": False}],
        }

        result = format_movie_info(movie)
        expected = "• Test Movie (2023) - Missing: English"
        self.assertEqual(result, expected)

        # Test release_year field
        movie = {
            "title": "Test Movie",
            "release_year": 2023,
            "missing_subtitles": [{"name": "English", "forced": False, "hi": False}],
        }

        result = format_movie_info(movie)
        expected = "• Test Movie (2023) - Missing: English"
        self.assertEqual(result, expected)

    def test_format_movie_info_forced_subtitles(self):
        """Test movie info formatting with forced subtitles."""
        movie = {
            "title": "Test Movie",
            "year": 2023,
            "missing_subtitles": [{"name": "English", "forced": True, "hi": False}],
        }

        result = format_movie_info(movie)
        expected = "• Test Movie (2023) - Missing: English (Forced)"

        self.assertEqual(result, expected)

    def test_format_movie_info_hi_subtitles(self):
        """Test movie info formatting with hearing impaired subtitles."""
        movie = {
            "title": "Test Movie",
            "year": 2023,
            "missing_subtitles": [{"name": "English", "forced": False, "hi": True}],
        }

        result = format_movie_info(movie)
        expected = "• Test Movie (2023) - Missing: English (HI)"

        self.assertEqual(result, expected)

    def test_format_movie_info_forced_and_hi(self):
        """Test movie info formatting with both forced and HI subtitles."""
        movie = {
            "title": "Test Movie",
            "year": 2023,
            "missing_subtitles": [{"name": "English", "forced": True, "hi": True}],
        }

        result = format_movie_info(movie)
        expected = "• Test Movie (2023) - Missing: English (Forced) (HI)"

        self.assertEqual(result, expected)

    def test_format_movie_info_multiple_languages(self):
        """Test movie info formatting with multiple missing subtitles."""
        movie = {
            "title": "Test Movie",
            "year": 2023,
            "missing_subtitles": [
                {"name": "English", "forced": False, "hi": False},
                {"name": "Spanish", "forced": True, "hi": False},
                {"name": "French", "forced": False, "hi": True},
            ],
        }

        result = format_movie_info(movie)
        expected = (
            "• Test Movie (2023) - Missing: English, Spanish (Forced), French (HI)"
        )

        self.assertEqual(result, expected)

    def test_format_movie_info_unknown_title(self):
        """Test movie info formatting with missing title."""
        movie = {
            "year": 2023,
            "missing_subtitles": [{"name": "English", "forced": False, "hi": False}],
        }

        result = format_movie_info(movie)
        expected = "• Unknown Title (2023) - Missing: English"

        self.assertEqual(result, expected)

    def test_format_movie_info_unknown_language(self):
        """Test movie info formatting with missing language name."""
        movie = {
            "title": "Test Movie",
            "year": 2023,
            "missing_subtitles": [{"forced": False, "hi": False}],
        }

        result = format_movie_info(movie)
        expected = "• Test Movie (2023) - Missing: Unknown"

        self.assertEqual(result, expected)

    def test_format_movie_info_no_missing_subtitles(self):
        """Test movie info formatting with no missing subtitles."""
        movie = {"title": "Test Movie", "year": 2023, "missing_subtitles": []}

        result = format_movie_info(movie)
        expected = "• Test Movie (2023) - Missing: Unknown"

        self.assertEqual(result, expected)

    def test_format_movie_info_missing_subtitles_key(self):
        """Test movie info formatting with missing subtitles key."""
        movie = {"title": "Test Movie", "year": 2023}

        result = format_movie_info(movie)
        expected = "• Test Movie (2023) - Missing: Unknown"

        self.assertEqual(result, expected)

    def test_format_movie_info_title_with_spaces(self):
        """Test movie info formatting with title containing extra spaces."""
        movie = {
            "title": "  Test Movie  ",
            "year": 2023,
            "missing_subtitles": [{"name": "English", "forced": False, "hi": False}],
        }

        result = format_movie_info(movie)
        expected = "• Test Movie (2023) - Missing: English"

        self.assertEqual(result, expected)

    def test_format_movie_info_year_priority(self):
        """Test year field priority when multiple year fields exist."""
        movie = {
            "title": "Test Movie",
            "year": 2023,
            "movie_year": 2022,
            "releaseYear": 2021,
            "release_year": 2020,
            "missing_subtitles": [{"name": "English", "forced": False, "hi": False}],
        }

        result = format_movie_info(movie)
        expected = "• Test Movie (2023) - Missing: English"

        # Should use "year" field first
        self.assertEqual(result, expected)


if __name__ == "__main__":
    unittest.main()
