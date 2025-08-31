"""
Tests for core.tracking module.
"""

import json
import shutil
import tempfile
import unittest
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import patch

from core.tracking import SubtitleTracker


class TestSubtitleTracker(unittest.TestCase):
    """Test cases for subtitle tracking functionality."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.tracking_file = Path(self.temp_dir) / "test_tracking.json"

        # Mock the config directory
        with patch("core.tracking.Path.home") as mock_home:
            mock_home.return_value = Path(self.temp_dir)
            self.tracker = SubtitleTracker()
            # Override the tracking file path for testing
            self.tracker.tracking_file = self.tracking_file

    def tearDown(self):
        """Clean up test fixtures."""
        if self.tracking_file.exists():
            self.tracking_file.unlink()
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_get_movie_key(self):
        """Test movie key generation."""
        # Test normal movie title
        key = self.tracker._get_movie_key("The Matrix")
        self.assertEqual(key, "the matrix")

        # Test movie with special characters
        key = self.tracker._get_movie_key("Spider-Man: No Way Home (2021)")
        self.assertEqual(key, "spider-man: no way home (2021)")

        # Test movie with multiple spaces
        key = self.tracker._get_movie_key("  The   Lord   of   the   Rings  ")
        self.assertEqual(key, "the lord of the rings")

    def test_load_tracking_data_new_file(self):
        """Test loading tracking data when file doesn't exist."""
        data = self.tracker._load_tracking_data()
        self.assertEqual(data, {})

    def test_load_tracking_data_existing_file(self):
        """Test loading tracking data from existing file."""
        test_data = {
            "test movie": [
                {"language": "english", "last_searched": "2023-01-01T12:00:00"}
            ]
        }

        with open(self.tracking_file, "w") as f:
            json.dump(test_data, f)

        data = self.tracker._load_tracking_data()
        self.assertEqual(data, test_data)

    def test_load_tracking_data_invalid_json(self):
        """Test loading tracking data handles invalid JSON."""
        # Write invalid JSON
        with open(self.tracking_file, "w") as f:
            f.write("invalid json content")

        data = self.tracker._load_tracking_data()
        self.assertEqual(data, {})

    def test_save_tracking_data(self):
        """Test saving tracking data."""
        test_data = {
            "test movie": [
                {"language": "english", "last_searched": "2023-01-01T12:00:00"}
            ]
        }

        self.tracker.data = test_data
        self.tracker._save_tracking_data()

        # Verify file was created and contains correct data
        self.assertTrue(self.tracking_file.exists())

        with open(self.tracking_file, "r") as f:
            saved_data = json.load(f)

        self.assertEqual(saved_data, test_data)

    def test_record_no_subtitles_found(self):
        """Test recording when no subtitles are found."""
        title = "Test Movie"
        year = 2023
        language = "english"

        self.tracker.record_no_subtitles_found(title, year, language)

        key = self.tracker._get_movie_key(title)
        self.assertIn(key, self.tracker.data)

        lang_entries = self.tracker.data[key]
        self.assertEqual(len(lang_entries), 1)
        self.assertEqual(lang_entries[0]["language"], language)
        self.assertIn("last_no_subtitles", lang_entries[0])

    def test_record_download_success(self):
        """Test recording successful subtitle download."""
        title = "Test Movie"
        year = 2023
        language = "english"
        filename = "test.srt"

        self.tracker.record_download_success(title, year, language, filename)

        key = self.tracker._get_movie_key(title)
        self.assertIn(key, self.tracker.data)

        lang_entries = self.tracker.data[key]
        self.assertEqual(len(lang_entries), 1)
        self.assertEqual(lang_entries[0]["language"], language)
        self.assertIn("last_download_success", lang_entries[0])
        self.assertEqual(lang_entries[0]["downloaded_filename"], filename)

    def test_record_download_failure(self):
        """Test recording failed subtitle download."""
        title = "Test Movie"
        year = 2023
        language = "english"
        error = "Network error"

        self.tracker.record_download_failure(title, year, language, error)

        key = self.tracker._get_movie_key(title)
        self.assertIn(key, self.tracker.data)

        lang_entries = self.tracker.data[key]
        self.assertEqual(len(lang_entries), 1)
        self.assertEqual(lang_entries[0]["language"], language)
        self.assertIn("last_download_failure", lang_entries[0])
        self.assertEqual(lang_entries[0]["last_error"], error)

    def test_get_last_no_subtitles_timestamp(self):
        """Test getting last no subtitles timestamp."""
        title = "Test Movie"
        year = 2023
        language = "english"

        # Test when no record exists
        timestamp = self.tracker.get_last_no_subtitles_timestamp(title, year, language)
        self.assertIsNone(timestamp)

        # Add a record and test again
        self.tracker.record_no_subtitles_found(title, year, language)
        timestamp = self.tracker.get_last_no_subtitles_timestamp(title, year, language)
        self.assertIsNotNone(timestamp)

    def test_get_last_success_timestamp(self):
        """Test getting last success timestamp."""
        title = "Test Movie"
        year = 2023
        language = "english"
        filename = "test.srt"

        # Test when no record exists
        timestamp = self.tracker.get_last_success_timestamp(title, year, language)
        self.assertIsNone(timestamp)

        # Add a record and test again
        self.tracker.record_download_success(title, year, language, filename)
        timestamp = self.tracker.get_last_success_timestamp(title, year, language)
        self.assertIsNotNone(timestamp)

    @patch("core.tracking.datetime")
    def test_should_skip_search_recent_failure(self, mock_datetime):
        """Test should_skip_search with recent failure."""
        # Mock current time
        current_time = datetime(2023, 1, 1, 12, 0, 0)
        mock_datetime.now.return_value = current_time
        mock_datetime.fromisoformat.side_effect = datetime.fromisoformat

        title = "Test Movie"
        year = 2023
        language = "english"

        # Record a recent failure (1 hour ago)
        failure_time = current_time - timedelta(hours=1)
        key = self.tracker._get_movie_key(title)
        self.tracker.data[key] = [
            {"language": language, "last_no_subtitles": failure_time.isoformat()}
        ]

        # Should skip if threshold is 2 hours
        should_skip = self.tracker.should_skip_search(title, year, language, 2)
        self.assertTrue(should_skip)

        # Should not skip if threshold is 0.5 hours
        should_skip = self.tracker.should_skip_search(title, year, language, 0.5)
        self.assertFalse(should_skip)

    def test_should_skip_search_with_recent_success(self):
        """Test should_skip_search when there's a recent success."""
        title = "Test Movie"
        year = 2023
        language = "english"
        filename = "test.srt"

        # Record a recent success
        self.tracker.record_download_success(title, year, language, filename)

        # Should not skip when there's a recent success
        should_skip = self.tracker.should_skip_search(title, year, language, 24)
        self.assertFalse(should_skip)

    def test_should_skip_search_no_history(self):
        """Test should_skip_search when no history exists."""
        title = "New Movie"
        year = 2023
        language = "english"

        # Should not skip when no history exists
        should_skip = self.tracker.should_skip_search(title, year, language, 24)
        self.assertFalse(should_skip)

    def test_update_existing_language_entry(self):
        """Test updating an existing language entry."""
        title = "Test Movie"
        year = 2023
        language = "english"

        # Record initial failure
        self.tracker.record_no_subtitles_found(title, year, language)

        # Record success for same movie/language
        filename = "test.srt"
        self.tracker.record_download_success(title, year, language, filename)

        key = self.tracker._get_movie_key(title)
        lang_entries = self.tracker.data[key]

        # Should still have only one entry for this language
        self.assertEqual(len(lang_entries), 1)
        self.assertEqual(lang_entries[0]["language"], language)

        # Should have both failure and success timestamps
        self.assertIn("last_no_subtitles", lang_entries[0])
        self.assertIn("last_download_success", lang_entries[0])
        self.assertEqual(lang_entries[0]["downloaded_filename"], filename)

    def test_multiple_languages_same_movie(self):
        """Test tracking multiple languages for the same movie."""
        title = "Test Movie"
        year = 2023

        # Record for different languages
        self.tracker.record_no_subtitles_found(title, year, "english")
        self.tracker.record_download_success(title, year, "spanish", "spanish.srt")

        key = self.tracker._get_movie_key(title)
        lang_entries = self.tracker.data[key]

        # Should have two language entries
        self.assertEqual(len(lang_entries), 2)

        languages = [entry["language"] for entry in lang_entries]
        self.assertIn("english", languages)
        self.assertIn("spanish", languages)


if __name__ == "__main__":
    unittest.main()
