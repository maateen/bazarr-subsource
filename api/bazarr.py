"""
Bazarr API client for interacting with Bazarr instance.
"""

import json
import logging
import os
import re
from typing import Dict, Optional

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

    def upload_subtitle_to_bazarr(
        self,
        radarr_id: int,
        subtitle_file: str,
        language: str,
        forced: bool = False,
        hi: bool = False,
    ) -> bool:
        """
        Upload a subtitle file to Bazarr.

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
