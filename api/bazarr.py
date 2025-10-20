"""
Bazarr API client for interacting with Bazarr instance.
"""

import json
import logging
import os
import re
from typing import Dict, List, Optional

import requests

logger = logging.getLogger(__name__)


class Bazarr:
    """Client for interacting with Bazarr API."""

    def __init__(self, bazarr_url: str, api_key: str, username: str, password: str):
        self.bazarr_url = bazarr_url
        self.api_key = api_key
        self.username = username
        self.password = password
        self.session = requests.Session()

        # Setup headers with connection optimization
        self.session.headers.update({"X-API-KEY": api_key, "Connection": "keep-alive"})

        # Setup authentication
        self.auth = requests.auth.HTTPBasicAuth(username, password)

    def get_wanted_movies(self, start: int = 0, length: int = -1) -> Optional[Dict]:
        """
        Fetch wanted movies from Bazarr API.

        Args:
            start: Paging start integer (default: 0)
            length: Paging length integer (default: -1 for all)

        Returns:
            JSON response from API or None if error
        """
        url = f"{self.bazarr_url}/api/movies/wanted"
        params = {"start": start, "length": length}

        try:
            response = self.session.get(url, params=params, auth=self.auth, timeout=30)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"Error connecting to Bazarr API: {e}")
            return None
        except json.JSONDecodeError as e:
            logger.error(f"Error parsing JSON response: {e}")
            return None

    def upload_movie_subtitle(
        self,
        radarr_id: int,
        subtitle_file: str,
        language: str,
        forced: bool = False,
        hi: bool = False,
    ) -> bool:
        """
        Upload a subtitle file for a movie to Bazarr.

        Args:
            radarr_id: Radarr movie ID
            subtitle_file: Path to subtitle file
            language: Language code (e.g., 'en')
            forced: Whether subtitle is forced
            hi: Whether subtitle is hearing impaired

        Returns:
            True if successful, False otherwise
        """
        try:
            url = f"{self.bazarr_url}/api/movies/subtitles"

            # Prepare form data
            data = {
                "radarrid": radarr_id,
                "language": language,
                "forced": "true" if forced else "false",
                "hi": "true" if hi else "false",
            }

            # Upload file
            with open(subtitle_file, "rb") as f:
                files = {"file": (os.path.basename(subtitle_file), f, "text/plain")}

                response = self.session.post(
                    url, data=data, files=files, auth=self.auth, timeout=30
                )
                response.raise_for_status()

                print("    ✓ Uploaded subtitle to Bazarr")
                return True

        except requests.exceptions.RequestException as e:
            print(f"    ✗ Error uploading to Bazarr: {e}")
            return False
        except IOError as e:
            print(f"    ✗ Error reading subtitle file: {e}")
            return False

    def sync_subtitle(
        self,
        subtitle_path: str,
        media_type: str,
        media_id: int,
        language: str,
        forced: bool = False,
        hi: bool = False,
        reference: str = "a:0",
        max_offset_seconds: int = 300,
        no_fix_framerate: bool = False,
        use_gss: bool = False,
    ) -> bool:
        """
        Synchronize a subtitle file using Bazarr's sync functionality.

        Args:
            subtitle_path: Path to the subtitle file on the Bazarr server
            media_type: Either "movie" or "episode"
            media_id: Media ID (radarrId for movies, episodeId for episodes)
            language: Language code (e.g., 'en')
            forced: Whether subtitle is forced
            hi: Whether subtitle is hearing impaired
            reference: Reference for sync (e.g., 'a:0' for first audio track)
            max_offset_seconds: Maximum offset seconds to allow
            no_fix_framerate: Don't try to fix framerate issues
            use_gss: Use Golden-Section Search algorithm

        Returns:
            True if successful, False otherwise
        """
        try:
            url = f"{self.bazarr_url}/api/subtitles"

            # Prepare sync parameters
            params = {
                "action": "sync",
                "language": language,
                "path": subtitle_path,
                "type": media_type,
                "id": media_id,
                "forced": "true" if forced else "false",
                "hi": "true" if hi else "false",
                "reference": reference,
                "max_offset_seconds": str(max_offset_seconds),
                "no_fix_framerate": "true" if no_fix_framerate else "false",
                "gss": "true" if use_gss else "false",
            }

            response = self.session.patch(
                url, params=params, auth=self.auth, timeout=300
            )
            response.raise_for_status()

            print("    ✓ Synchronized subtitle with Bazarr")
            return True

        except requests.exceptions.RequestException as e:
            print(f"    ✗ Error synchronizing subtitle: {e}")
            return False

    def trigger_subzero_mods(
        self,
        subtitle_path: str,
        media_type: str,
        media_id: int,
        language: str,
        forced: bool = False,
        hi: bool = False,
    ) -> bool:
        """
        Trigger Sub-Zero subtitle modifications using Bazarr's API.

        Args:
            subtitle_path: Path to the subtitle file on the Bazarr server
            media_type: Either "movie" or "episode"
            media_id: Media ID (radarrId for movies, episodeId for episodes)
            language: Language code (e.g., 'en')
            forced: Whether subtitle is forced
            hi: Whether subtitle is hearing impaired

        Returns:
            True if successful, False otherwise
        """
        try:
            url = f"{self.bazarr_url}/api/subtitles"

            # Prepare Sub-Zero modification parameters
            params = {
                "action": "subzero",
                "language": language,
                "path": subtitle_path,
                "type": media_type,
                "id": media_id,
                "forced": "true" if forced else "false",
                "hi": "true" if hi else "false",
            }

            response = self.session.patch(
                url, params=params, auth=self.auth, timeout=60
            )
            response.raise_for_status()

            print("    ✓ Applied Sub-Zero modifications")
            return True

        except requests.exceptions.RequestException as e:
            print(f"    ✗ Error applying Sub-Zero modifications: {e}")
            return False

    def get_movie_subtitles(self, radarr_id: int) -> Optional[Dict]:
        """
        Get movie details including subtitle information.

        Args:
            radarr_id: Radarr movie ID

        Returns:
            Movie data with subtitle paths or None if error
        """
        try:
            url = f"{self.bazarr_url}/api/movies"
            params = {"radarrid[]": radarr_id}

            response = self.session.get(url, params=params, auth=self.auth, timeout=30)
            response.raise_for_status()

            data = response.json()
            if data and "data" in data and data["data"]:
                return data["data"][0]  # Return first (and only) movie
            return None

        except requests.exceptions.RequestException as e:
            logger.error(f"Error getting movie subtitles: {e}")
            return None
        except (json.JSONDecodeError, KeyError, IndexError) as e:
            logger.error(f"Error parsing movie subtitles response: {e}")
            return None

    def get_system_settings(self) -> Optional[Dict]:
        """
        Get system settings from Bazarr.

        Returns:
            Dictionary containing system settings or None if error
        """
        try:
            url = f"{self.bazarr_url}/api/system/settings"
            response = self.session.get(url, auth=self.auth, timeout=30)
            response.raise_for_status()
            return response.json()
        except (requests.exceptions.RequestException, json.JSONDecodeError) as e:
            logger.error(f"Error fetching system settings: {e}")
            return None

    def get_sync_settings(self) -> Dict:
        """
        Get subtitle synchronization settings from Bazarr's system settings.

        Returns:
            Dictionary containing sync settings with defaults if not available
        """
        settings = self.get_system_settings()
        if not settings or "subsync" not in settings:
            logger.warning("Could not fetch sync settings from Bazarr, using defaults")
            return {
                "enabled": False,
                "max_offset_seconds": 300,
                "no_fix_framerate": False,
                "use_gss": False,
                "reference": "a:0",
            }

        subsync = settings["subsync"]
        return {
            "enabled": subsync.get("use_subsync", False),
            "max_offset_seconds": subsync.get("max_offset_seconds", 300),
            "no_fix_framerate": subsync.get("no_fix_framerate", False),
            "use_gss": subsync.get("gss", False),
            "reference": "a:0",  # Always use first audio track as reference
        }

    def get_subzero_settings(self) -> Dict:
        """
        Get Sub-Zero subtitle modification settings from Bazarr's system settings.

        Returns:
            Dictionary containing Sub-Zero settings with defaults if not available
        """
        settings = self.get_system_settings()
        if not settings or "general" not in settings:
            logger.warning(
                "Could not fetch Sub-Zero settings from Bazarr, using defaults"
            )
            return {"mods": [], "enabled": False}

        general = settings["general"]
        subzero_mods = general.get("subzero_mods", [])

        return {"mods": subzero_mods, "enabled": len(subzero_mods) > 0}

    def get_system_tasks(self) -> Optional[Dict]:
        """
        Fetch system tasks from Bazarr API to get search intervals.

        Returns:
            JSON response from API or None if error
        """
        url = f"{self.bazarr_url}/api/system/tasks"

        try:
            response = self.session.get(url, auth=self.auth, timeout=30)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"Error connecting to Bazarr system tasks API: {e}")
            return None
        except json.JSONDecodeError as e:
            logger.error(f"Error parsing system tasks JSON response: {e}")
            return None

    def get_missing_subtitles_search_interval(self) -> int:
        """
        Get the interval for "Search for Missing Movies Subtitles" task from Bazarr.

        Returns:
            Interval in hours, defaults to 24 if not found or error
        """
        tasks = self.get_system_tasks()

        if not tasks:
            logger.warning(
                "Could not fetch system tasks, using default 24 hour interval"
            )
            return 24

        # Handle different response formats - could be list or dict
        if isinstance(tasks, dict):
            # If it's a dict, look for 'data' or 'tasks' key, or iterate over values
            if "data" in tasks:
                task_list = tasks["data"]
            elif "tasks" in tasks:
                task_list = tasks["tasks"]
            else:
                # Assume the dict values are the tasks
                task_list = list(tasks.values())
        elif isinstance(tasks, list):
            task_list = tasks
        else:
            logger.warning(
                f"Unexpected tasks response format: {type(tasks)}, "
                "using default 24 hour interval"
            )
            return 24

        # Look for the missing subtitles search task
        search_task_names = [
            "Search for Missing Movies Subtitles",
            "missing_subtitles_movies",
            "wanted_search_movie",
        ]

        for task in task_list:
            # Skip if task is not a dict
            if not isinstance(task, dict):
                logger.debug(f"Skipping non-dict task: {task}")
                continue

            task_name = task.get("name", "")
            task_job_id = task.get("job_id", "")

            if any(
                search_name.lower() in task_name.lower()
                for search_name in search_task_names
            ) or any(
                search_name.lower() in task_job_id.lower()
                for search_name in search_task_names
            ):
                # Get interval - could be in different formats
                interval_str = task.get("interval", "")

                if not interval_str:
                    logger.warning(
                        f"No interval found for task {task_name}, "
                        "using default 24 hours"
                    )
                    return 24

                # Parse interval string (could be like "24:00:00", "24h", "1440m", etc.)
                try:
                    minutes = self._parse_interval_to_minutes(interval_str)
                    hours = minutes // 60
                    logger.info(
                        f"Found Bazarr missing subtitles search interval: "
                        f"{hours} hours ({interval_str})"
                    )
                    return hours
                except ValueError as e:
                    logger.warning(
                        f"Could not parse interval '{interval_str}': {e}, "
                        "using default 24 hours"
                    )
                    return 24

        logger.warning(
            "Could not find missing subtitles search task, "
            "using default 24 hour interval"
        )
        return 24

    def _parse_interval_to_minutes(self, interval_str: str) -> int:
        """
        Parse various interval string formats to minutes.

        Args:
            interval_str: Interval string (e.g., "24:00:00", "24h", "1440m",
                         "86400s", "every Sunday at 3:00", "every 24 hours",
                         "every day at 5:00", "every 15 minutes")

        Returns:
            Minutes as integer

        Raises:
            ValueError: If format is not recognized
        """
        interval_str = interval_str.strip().lower()

        # Handle "every" formats
        if interval_str.startswith("every"):
            # Handle "every X hours"
            if "hours" in interval_str:
                # Extract number before "hours"
                match = re.search(r"every\s+(\d+)\s+hours?", interval_str)
                if match:
                    return int(match.group(1)) * 60  # Convert hours to minutes

            # Handle "every X minutes"
            elif "minutes" in interval_str:
                match = re.search(r"every\s+(\d+)\s+minutes?", interval_str)
                if match:
                    return int(match.group(1))  # Already in minutes

            # Handle "every sunday" or other weekly patterns first
            # (weekly = 168 hours = 10080 minutes)
            elif any(
                day in interval_str
                for day in [
                    "sunday",
                    "monday",
                    "tuesday",
                    "wednesday",
                    "thursday",
                    "friday",
                    "saturday",
                ]
            ):
                # 7 days * 24 hours * 60 minutes = 10080 minutes
                return 168 * 60

            # Handle "every day" (daily = 24 hours = 1440 minutes)
            elif "day" in interval_str:
                return 24 * 60  # 1440 minutes

        # Handle HH:MM:SS format
        if ":" in interval_str:
            parts = interval_str.split(":")
            if len(parts) >= 2:
                hours = int(parts[0])
                minutes = int(parts[1])
                # Convert to total minutes
                return hours * 60 + minutes
            elif len(parts) == 1:
                # Assume hours, convert to minutes
                return int(parts[0]) * 60

        # Handle suffixed formats (24h, 1440m, 86400s)
        if interval_str.endswith("h"):
            # Convert hours to minutes
            return int(interval_str[:-1]) * 60
        elif interval_str.endswith("m"):
            # Already in minutes
            return int(interval_str[:-1])
        elif interval_str.endswith("s"):
            # Convert seconds to minutes
            return int(interval_str[:-1]) // 60
        elif interval_str.isdigit():
            # Assume it's hours if just a number, convert to minutes
            return int(interval_str) * 60

        raise ValueError(f"Unrecognized interval format: {interval_str}")

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
            url = f"{self.bazarr_url}/api/episodes/wanted"
            params = {"start": start, "length": length}

            response = self.session.get(url, params=params, auth=self.auth, timeout=30)
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
        Enrich episode data with series information.

        Args:
            episode: Raw episode data from Bazarr

        Returns:
            Enriched episode data or None
        """
        season, episode_number = episode.get("episode_number", "").split("x")
        enriched_episode = {
            "series_title": episode.get("seriesTitle", "Unknown Series").strip(),
            "season": season,
            "episode_number": episode_number,
            "episode_title": episode.get("episodeTitle", "Unknown Episode").strip(),
            "missing_subtitles": episode.get("missing_subtitles", []),
            "sonarr_series_id": episode.get("sonarrSeriesId", ""),
            "sonarr_episode_id": episode.get("sonarrEpisodeId", ""),
            "scene_name": episode.get("sceneName", ""),
            "tags": episode.get("tags", []),
            "series_type": episode.get("seriesType", "standard"),
        }

        try:
            # Get more series information
            series_info = self.get_series_info(enriched_episode["sonarr_series_id"])
            if series_info:
                enriched_episode["year"] = series_info.get("year")
                enriched_episode["imdb"] = series_info.get("imdbId")
                enriched_episode["tvdb"] = series_info.get("tvdbId")

            return enriched_episode

        except Exception as e:
            logger.warning(f"Could not enrich episode data: {e}")
            return enriched_episode

    def get_series_info(self, series_id: int) -> Optional[Dict]:
        """
        Get series information from Bazarr.

        Args:
            series_id: Series ID

        Returns:
            Series information dictionary or None
        """
        try:
            url = f"{self.bazarr_url}/api/series"
            params = {"seriesid[]": series_id}

            response = self.session.get(url, params=params, auth=self.auth, timeout=30)
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
            url = f"{self.bazarr_url}/api/episodes/subtitles"

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
                    url, params=params, files=files, auth=self.auth, timeout=60
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

    def get_episode_search_interval(self) -> int:
        """
        Get episode search interval from Bazarr settings.

        Returns:
            Search interval in hours (default 24)
        """
        try:
            url = f"{self.bazarr_url}/api/system/settings"
            response = self.session.get(url, auth=self.auth, timeout=30)
            response.raise_for_status()

            settings = response.json()

            # Look for episode search interval setting
            # This might be under different keys depending on Bazarr version
            interval = settings.get("general", {}).get("episode_search_interval", 24)
            if isinstance(interval, str):
                interval = int(interval)

            return max(1, interval)  # Minimum 1 hour

        except Exception as e:
            logger.warning(f"Could not get episode search interval from Bazarr: {e}")
            return 24  # Default fallback

    def sync_episode_subtitle(
        self,
        subtitle_path: str,
        series_id: int,
        episode_id: int,
        language: str,
        forced: bool = False,
        hi: bool = False,
        reference: str = "a:0",
        max_offset_seconds: int = 300,
        no_fix_framerate: bool = False,
        use_gss: bool = False,
    ) -> bool:
        """
        Synchronize an episode subtitle file using Bazarr's sync functionality.

        Args:
            subtitle_path: Path to the subtitle file on the Bazarr server
            series_id: Sonarr series ID
            episode_id: Sonarr episode ID
            language: Language code (e.g., 'en')
            forced: Whether subtitle is forced
            hi: Whether subtitle is hearing impaired
            reference: Reference for sync (e.g., 'a:0' for first audio track)
            max_offset_seconds: Maximum offset seconds to allow
            no_fix_framerate: Don't try to fix framerate issues
            use_gss: Use Golden-Section Search algorithm

        Returns:
            True if successful, False otherwise
        """
        try:
            url = f"{self.bazarr_url}/api/subtitles"

            # Prepare sync parameters
            params = {
                "action": "sync",
                "language": language,
                "path": subtitle_path,
                "type": "episode",
                "id": episode_id,
                "forced": "true" if forced else "false",
                "hi": "true" if hi else "false",
                "reference": reference,
                "max_offset_seconds": str(max_offset_seconds),
                "no_fix_framerate": "true" if no_fix_framerate else "false",
                "gss": "true" if use_gss else "false",
            }

            response = self.session.patch(
                url, params=params, auth=self.auth, timeout=300
            )
            response.raise_for_status()

            print("    ✓ Synchronized episode subtitle with Bazarr")
            return True

        except requests.exceptions.RequestException as e:
            print(f"    ✗ Error synchronizing episode subtitle: {e}")
            return False

    def trigger_episode_subzero_mods(
        self,
        subtitle_path: str,
        series_id: int,
        episode_id: int,
        language: str,
        forced: bool = False,
        hi: bool = False,
    ) -> bool:
        """
        Trigger Sub-Zero subtitle modifications for an episode using Bazarr's API.

        Args:
            subtitle_path: Path to the subtitle file on the Bazarr server
            series_id: Sonarr series ID
            episode_id: Sonarr episode ID
            language: Language code (e.g., 'en')
            forced: Whether subtitle is forced
            hi: Whether subtitle is hearing impaired

        Returns:
            True if successful, False otherwise
        """
        try:
            url = f"{self.bazarr_url}/api/subtitles"

            # Prepare Sub-Zero modification parameters
            params = {
                "action": "subzero",
                "language": language,
                "path": subtitle_path,
                "type": "episode",
                "id": episode_id,
                "forced": "true" if forced else "false",
                "hi": "true" if hi else "false",
            }

            response = self.session.patch(
                url, params=params, auth=self.auth, timeout=60
            )
            response.raise_for_status()

            print("    ✓ Applied Sub-Zero modifications to episode")
            return True

        except requests.exceptions.RequestException as e:
            print(f"    ✗ Error applying Sub-Zero modifications to episode: {e}")
            return False

    def get_episode_subtitles(self, series_id: int, episode_id: int) -> Optional[Dict]:
        """
        Get episode details including subtitle information.

        Args:
            series_id: Sonarr series ID
            episode_id: Sonarr episode ID

        Returns:
            Episode data with subtitle paths or None if error
        """
        try:
            url = f"{self.bazarr_url}/api/episodes"
            params = {"seriesid[]": series_id, "episodeid[]": episode_id}

            response = self.session.get(url, params=params, auth=self.auth, timeout=30)
            response.raise_for_status()

            data = response.json()
            if data and "data" in data and data["data"]:
                return data["data"][0]  # Return first (and only) episode
            return None

        except requests.exceptions.RequestException as e:
            logger.error(f"Error getting episode subtitles: {e}")
            return None
        except (KeyError, IndexError) as e:
            logger.error(f"Error parsing episode subtitles response: {e}")
            return None
