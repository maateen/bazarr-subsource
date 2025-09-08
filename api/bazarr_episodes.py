"""
Bazarr API client for TV show episodes.
"""

import logging
from typing import Dict, List, Optional

import requests

logger = logging.getLogger(__name__)


class BazarrEpisodeClient:
    """Bazarr API client for episode operations."""

    def __init__(self, base_url: str, api_key: str, username: str, password: str):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.session = requests.Session()

        # Set up authentication
        if username and password:
            self.session.auth = (username, password)

        self.session.headers.update(
            {
                "X-API-KEY": api_key,
                "Content-Type": "application/json",
            }
        )

    def get_wanted_episodes(self, start: int = 0, length: int = -1) -> List[Dict]:
        """
        Get list of wanted episodes from Bazarr.

        Args:
            start: Paging start integer
            length: Paging length integer (-1 for all)

        Returns:
            List of wanted episode dictionaries
        """
        try:
            url = f"{self.base_url}/api/episodes/wanted"
            params = {"start": start, "length": length}

            response = self.session.get(url, params=params, timeout=30)
            response.raise_for_status()

            data = response.json()
            episodes = data.get("data", []) if isinstance(data, dict) else data

            # Enrich episode data with series information
            enriched_episodes = []
            for episode in episodes:
                enriched_episode = self._enrich_episode_data(episode)
                if enriched_episode:
                    enriched_episodes.append(enriched_episode)

            logger.info(f"Found {len(enriched_episodes)} wanted episodes")
            return enriched_episodes

        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching wanted episodes: {e}")
            return []

    def _enrich_episode_data(self, episode: Dict) -> Optional[Dict]:
        """
        Enrich episode data with additional series information.

        Args:
            episode: Raw episode data from Bazarr

        Returns:
            Enriched episode data or None if series info unavailable
        """
        series_id = episode.get("sonarrSeriesId") or episode.get("seriesId")
        if not series_id:
            logger.warning(
                f"No series ID found for episode: {episode.get('title', 'Unknown')}"
            )
            return episode

        try:
            # Get series information
            series_info = self.get_series_info(series_id)
            if series_info:
                episode["seriesTitle"] = series_info.get("title", "Unknown Series")
                episode["seriesYear"] = series_info.get("year")
                episode["seriesImdb"] = series_info.get("imdbId")

            return episode

        except Exception as e:
            logger.warning(f"Could not enrich episode data: {e}")
            return episode

    def get_series_info(self, series_id: int) -> Optional[Dict]:
        """
        Get series information from Bazarr.

        Args:
            series_id: Series ID

        Returns:
            Series information dictionary or None
        """
        try:
            url = f"{self.base_url}/api/series"
            params = {"seriesid[]": series_id}

            response = self.session.get(url, params=params, timeout=30)
            response.raise_for_status()

            data = response.json()
            series_list = data.get("data", []) if isinstance(data, dict) else data

            # Find the series with matching ID
            for series in series_list:
                if (
                    series.get("sonarrSeriesId") == series_id
                    or series.get("seriesId") == series_id
                ):
                    return series

            return None

        except requests.exceptions.RequestException as e:
            logger.warning(f"Error fetching series info for ID {series_id}: {e}")
            return None

    def upload_episode_subtitle(
        self,
        series_id: int,
        episode_id: int,
        language: str,
        subtitle_file: str,
        forced: bool = False,
        hi: bool = False,
    ) -> bool:
        """
        Upload a subtitle file for an episode to Bazarr.

        Args:
            series_id: Series ID
            episode_id: Episode ID
            language: Language code (e.g., 'en')
            subtitle_file: Path to subtitle file
            forced: Whether subtitle is forced
            hi: Whether subtitle is hearing impaired

        Returns:
            True if upload successful, False otherwise
        """
        try:
            url = f"{self.base_url}/api/episodes/subtitles"

            params = {
                "seriesid": series_id,
                "episodeid": episode_id,
                "language": language,
                "forced": "true" if forced else "false",
                "hi": "true" if hi else "false",
            }

            with open(subtitle_file, "rb") as f:
                files = {"file": (subtitle_file, f, "text/plain")}

                response = self.session.post(
                    url, params=params, files=files, timeout=60
                )
                response.raise_for_status()

            logger.info(
                f"Successfully uploaded subtitle for episode {episode_id}: "
                f"{subtitle_file}"
            )
            return True

        except requests.exceptions.RequestException as e:
            logger.error(f"Error uploading episode subtitle: {e}")
            return False
        except FileNotFoundError:
            logger.error(f"Subtitle file not found: {subtitle_file}")
            return False

    def get_search_interval(self) -> int:
        """
        Get search interval from Bazarr settings.

        Returns:
            Search interval in hours (default 24)
        """
        try:
            url = f"{self.base_url}/api/system/settings"
            response = self.session.get(url, timeout=30)
            response.raise_for_status()

            settings = response.json()

            # Look for episode search interval setting
            # This might be under different keys depending on Bazarr version
            interval = settings.get("general", {}).get("episode_search_interval", 24)
            if isinstance(interval, str):
                interval = int(interval)

            return max(1, interval)  # Minimum 1 hour

        except Exception as e:
            logger.warning(f"Could not get search interval from Bazarr: {e}")
            return 24  # Default fallback
