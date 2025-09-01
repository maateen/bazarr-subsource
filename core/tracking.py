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
            with open(self.tracking_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                logger.debug(f"Loaded tracking data: {len(data)} entries")
                return data
        except (json.JSONDecodeError, IOError) as e:
            logger.warning(f"Error loading tracking data: {e}")
            return {}

    def _save_tracking_data(self):
        """Save tracking data to file."""
        try:
            with open(self.tracking_file, "w", encoding="utf-8") as f:
                json.dump(self.data, f, indent=2, ensure_ascii=False)
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

        lang_entry["last_searched"] = timestamp

        logger.info(f"Recorded no subtitles found: {title} - {language} at {timestamp}")
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

    def remove_successful_download(self, title: str, year: int, language: str) -> bool:
        """
        Remove tracking entry for successful download to clean up database.

        Args:
            title: Movie title
            year: Movie year
            language: Subtitle language

        Returns:
            True if entry was removed, False if not found
        """
        key = self._get_movie_key(title)
        movie_data = self.data.get(key, [])

        # Find and remove the language entry
        for i, entry in enumerate(movie_data):
            if entry.get("language") == language:
                movie_data.pop(i)
                logger.info(
                    f"Removed tracking entry for successful download: "
                    f"{title} - {language}"
                )

                # If no more language entries for this movie, remove the movie key
                if not movie_data:
                    del self.data[key]
                    logger.info(f"Removed movie from tracking: {title}")

                self._save_tracking_data()
                return True

        return False

    def cleanup_obsolete_movies(self, current_wanted_movies: list) -> int:
        """
        Remove tracking entries for movies no longer in the wanted list.

        Args:
            current_wanted_movies: List of current wanted movies from Bazarr API

        Returns:
            Number of obsolete movies removed from tracking
        """
        if not current_wanted_movies:
            return 0

        # Create set of current wanted movie keys for fast lookup
        current_movie_keys = set()
        for movie in current_wanted_movies:
            title = movie.get("title", "")
            if title:
                current_movie_keys.add(self._get_movie_key(title))

        # Find obsolete entries
        obsolete_keys = []
        for movie_key in self.data.keys():
            if movie_key not in current_movie_keys:
                obsolete_keys.append(movie_key)

        # Remove obsolete entries
        removed_count = 0
        for key in obsolete_keys:
            del self.data[key]
            removed_count += 1
            logger.info(f"Removed obsolete tracking entry: {key}")

        if removed_count > 0:
            self._save_tracking_data()
            logger.info(
                f"Cleaned up {removed_count} obsolete movie(s) from tracking database"
            )

        return removed_count

    def get_last_searched_timestamp(
        self, title: str, year: int, language: str
    ) -> Optional[str]:
        """Get the last timestamp when subtitles were searched for."""
        key = self._get_movie_key(title)
        movie_data = self.data.get(key, [])

        for entry in movie_data:
            if entry.get("language") == language:
                return entry.get("last_searched")

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
        last_searched = self.get_last_searched_timestamp(title, year, language)

        # If we don't have a search record, don't skip
        if not last_searched:
            return False

        try:
            last_search_time = datetime.fromisoformat(last_searched)
            time_diff = datetime.now() - last_search_time

            # Skip if search was within the threshold
            if time_diff.total_seconds() < (hours_threshold * 3600):
                logger.info(
                    f"Skipping search for {title} ({year}) - {language} "
                    f"(last searched {time_diff} ago)"
                )
                return True
        except ValueError:
            logger.warning(f"Invalid timestamp format: {last_searched}")

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
