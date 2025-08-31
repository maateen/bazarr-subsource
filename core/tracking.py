"""
Tracking module for recording subtitle search failures and successes.
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional

logger = logging.getLogger(__name__)


class SubtitleTracker:
    """Track subtitle search results to avoid repeated searches."""

    def __init__(self):
        self.config_dir = Path.home() / ".config" / "bazarr-subsource"
        self.tracking_file = self.config_dir / "tracking.json"
        self.config_dir.mkdir(parents=True, exist_ok=True)
        self.data = self._load_tracking_data()

    def _load_tracking_data(self) -> Dict:
        """Load tracking data from file."""
        if not self.tracking_file.exists():
            return {}

        try:
            with open(self.tracking_file, "r") as f:
                data = json.load(f)
                logger.debug(f"Loaded tracking data: {len(data)} entries")
                return data
        except (json.JSONDecodeError, IOError) as e:
            logger.warning(f"Error loading tracking data: {e}")
            return {}

    def _save_tracking_data(self):
        """Save tracking data to file."""
        try:
            with open(self.tracking_file, "w") as f:
                json.dump(self.data, f, indent=2)
                logger.debug(f"Saved tracking data: {len(self.data)} entries")
        except IOError as e:
            logger.error(f"Error saving tracking data: {e}")

    def _get_movie_key(self, title: str) -> str:
        """Generate unique key for movie."""
        import re

        return re.sub(r"\s+", " ", title.lower().strip())

    def record_no_subtitles_found(self, title: str, year: int, language: str):
        """Record when no subtitles are found for a movie/language."""
        key = self._get_movie_key(title)
        timestamp = datetime.now().isoformat()

        if key not in self.data:
            self.data[key] = []

        # Find existing language entry or create new one
        lang_entry = None
        for entry in self.data[key]:
            if entry.get("language") == language:
                lang_entry = entry
                break

        if not lang_entry:
            lang_entry = {"language": language}
            self.data[key].append(lang_entry)

        lang_entry["last_no_subtitles"] = timestamp

        logger.info(f"Recorded no subtitles found: {title} - {language} at {timestamp}")
        self._save_tracking_data()

    def record_subtitles_found(self, title: str, year: int, language: str, count: int):
        """Record when subtitles are found for a movie/language."""
        key = self._get_movie_key(title)
        timestamp = datetime.now().isoformat()

        if key not in self.data:
            self.data[key] = []

        # Find existing language entry or create new one
        lang_entry = None
        for entry in self.data[key]:
            if entry.get("language") == language:
                lang_entry = entry
                break

        if not lang_entry:
            lang_entry = {"language": language}
            self.data[key].append(lang_entry)

        lang_entry["last_searched"] = timestamp
        lang_entry["subtitles_found"] = count

        # Remove last_searched if we found subtitles (successful search)
        if "last_no_subtitles_found" in lang_entry:
            del lang_entry["last_no_subtitles_found"]

        logger.info(
            f"Recorded {count} subtitles found: {title} - {language} at {timestamp}"
        )
        self._save_tracking_data()

    def record_download_success(
        self, title: str, year: int, language: str, filename: str
    ):
        """Record successful subtitle download."""
        key = self._get_movie_key(title)
        timestamp = datetime.now().isoformat()

        if key not in self.data:
            self.data[key] = []

        # Find existing language entry or create new one
        lang_entry = None
        for entry in self.data[key]:
            if entry.get("language") == language:
                lang_entry = entry
                break

        if not lang_entry:
            lang_entry = {"language": language}
            self.data[key].append(lang_entry)

        lang_entry["last_download_success"] = timestamp
        lang_entry["downloaded_filename"] = filename

        logger.info(
            f"Recorded download success: {title} - {language} -> {filename} "
            f"at {timestamp}"
        )
        self._save_tracking_data()

    def record_download_failure(self, title: str, year: int, language: str, error: str):
        """Record failed subtitle download."""
        key = self._get_movie_key(title)
        timestamp = datetime.now().isoformat()

        if key not in self.data:
            self.data[key] = []

        # Find existing language entry or create new one
        lang_entry = None
        for entry in self.data[key]:
            if entry.get("language") == language:
                lang_entry = entry
                break

        if not lang_entry:
            lang_entry = {"language": language}
            self.data[key].append(lang_entry)

        lang_entry["last_download_failure"] = timestamp
        lang_entry["last_error"] = error

        logger.info(
            f"Recorded download failure: {title} - {language}: {error} at {timestamp}"
        )
        self._save_tracking_data()

    def get_last_no_subtitles_timestamp(
        self, title: str, year: int, language: str
    ) -> Optional[str]:
        """Get the last timestamp when no subtitles were found."""
        key = self._get_movie_key(title)
        movie_data = self.data.get(key, [])

        for entry in movie_data:
            if entry.get("language") == language:
                return entry.get("last_no_subtitles")

        return None

    def get_last_success_timestamp(
        self, title: str, year: int, language: str
    ) -> Optional[str]:
        """Get the last timestamp when subtitles were successfully downloaded."""
        key = self._get_movie_key(title)
        movie_data = self.data.get(key, [])

        for entry in movie_data:
            if entry.get("language") == language:
                return entry.get("last_download_success")

        return None

    def should_skip_search(
        self, title: str, year: int, language: str, hours_threshold: int
    ) -> bool:
        """
        Check if we should skip searching for subtitles based on recent failures.
        Uses Bazarr's own search interval to determine if enough time has passed.

        Args:
            title: Movie title
            year: Movie year
            language: Subtitle language
            hours_threshold: Skip if no subtitles found within this many hours
                (from Bazarr interval)

        Returns:
            True if search should be skipped
        """
        last_no_subs = self.get_last_no_subtitles_timestamp(title, year, language)
        last_success = self.get_last_success_timestamp(title, year, language)

        # If we have a recent success, don't skip
        if last_success:
            return False

        # If we don't have a failure record, don't skip
        if not last_no_subs:
            return False

        try:
            last_failure_time = datetime.fromisoformat(last_no_subs)
            time_diff = datetime.now() - last_failure_time

            # Skip if failure was within the threshold
            if time_diff.total_seconds() < (hours_threshold * 3600):
                logger.info(
                    f"Skipping search for {title} ({year}) - {language} "
                    f"(last searched {time_diff} ago)"
                )
                return True
        except ValueError:
            logger.warning(f"Invalid timestamp format: {last_no_subs}")

        return False

    def get_tracking_summary(self) -> Dict:
        """Get summary statistics of tracking data."""
        total_movies = len(self.data)
        total_language_entries = sum(len(entries) for entries in self.data.values())
        no_subs_count = 0
        success_count = 0
        failure_count = 0

        for movie_entries in self.data.values():
            for entry in movie_entries:
                if "last_searched" in entry and "subtitles_found" not in entry:
                    no_subs_count += 1
                if "last_download_success" in entry:
                    success_count += 1
                if "last_download_failure" in entry:
                    failure_count += 1

        return {
            "total_tracked_movies": total_movies,
            "total_language_entries": total_language_entries,
            "searches_with_no_subtitles": no_subs_count,
            "successful_downloads": success_count,
            "failed_downloads": failure_count,
            "tracking_file": str(self.tracking_file),
        }
