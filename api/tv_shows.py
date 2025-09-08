"""
TV Show SubSource API client for downloading episode subtitles.
"""

import logging
import re
import time
from typing import Dict, List, Optional, Tuple

import requests

from core.tracking import SubtitleTracker

logger = logging.getLogger(__name__)


class TVShowSubSourceDownloader:
    """SubSource TV show subtitle downloader."""

    def __init__(self, api_url: str, download_dir: str, bazarr=None):
        self.api_url = api_url
        self.download_dir = download_dir
        self.session = requests.Session()
        self.tracker = SubtitleTracker()
        self.bazarr = bazarr
        self._search_interval_hours = None

    def _get_search_interval_hours(self) -> int:
        """Get search interval from Bazarr or use default."""
        if self._search_interval_hours is not None:
            return self._search_interval_hours

        # Try to get from Bazarr API if available
        if self.bazarr:
            try:
                search_interval = self.bazarr.get_search_interval()
                self._search_interval_hours = search_interval
                return search_interval
            except Exception as e:
                logger.warning(f"Could not get search interval from Bazarr: {e}")

        # Default fallback
        self._search_interval_hours = 24
        return self._search_interval_hours

    def _generate_episode_search_queries(self, episode: Dict) -> List[str]:
        """
        Generate search queries for an episode.

        Args:
            episode: Episode data from Bazarr

        Returns:
            List of search query strings
        """
        series_title = episode.get("seriesTitle", "")
        episode_title = episode.get("title", "")
        season = episode.get("season", 0)
        episode_num = episode.get("episode", 0)
        scene_name = episode.get("sceneName", "")

        queries = []

        if series_title:
            # Primary: Series + S01E01 format
            if season and episode_num:
                queries.append(f"{series_title} S{season:02d}E{episode_num:02d}")

            # Secondary: Series + episode title
            if episode_title:
                queries.append(f"{series_title} {episode_title}")

            # Tertiary: Just series name (less specific)
            queries.append(series_title)

        # Quaternary: Scene name if available
        if scene_name:
            # Extract show name from scene name
            scene_clean = re.sub(r"[.\-_]", " ", scene_name)
            queries.append(scene_clean)

        return queries

    def _extract_episode_info_from_subtitle(
        self, subtitle: Dict
    ) -> Tuple[Optional[int], Optional[int]]:
        """
        Extract season/episode info from subtitle release info.

        Args:
            subtitle: Subtitle data from SubSource

        Returns:
            Tuple of (season, episode) or (None, None) if not found
        """
        release_info = subtitle.get("release_info", "")

        # Look for S01E01 pattern
        season_episode_match = re.search(r"[Ss](\d+)[Ee](\d+)", release_info)
        if season_episode_match:
            season = int(season_episode_match.group(1))
            episode = int(season_episode_match.group(2))
            return season, episode

        # Look for 1x01 pattern
        alt_pattern = re.search(r"(\d+)x(\d+)", release_info)
        if alt_pattern:
            season = int(alt_pattern.group(1))
            episode = int(alt_pattern.group(2))
            return season, episode

        return None, None

    def _is_subtitle_match(self, subtitle: Dict, target_episode: Dict) -> bool:
        """
        Check if a subtitle matches the target episode.

        Args:
            subtitle: Subtitle data from SubSource
            target_episode: Episode data from Bazarr

        Returns:
            True if subtitle matches episode
        """
        target_season = target_episode.get("season")
        target_episode_num = target_episode.get("episode")

        if not target_season or not target_episode_num:
            return False

        sub_season, sub_episode = self._extract_episode_info_from_subtitle(subtitle)

        if sub_season == target_season and sub_episode == target_episode_num:
            return True

        return False

    def search_episode_subtitles(
        self, episode: Dict, language: str = "english"
    ) -> List[Dict]:
        """
        Search for subtitles for a specific episode.

        Args:
            episode: Episode data from Bazarr
            language: Subtitle language

        Returns:
            List of matching subtitle results
        """
        series_title = episode.get("seriesTitle", "Unknown")
        season = episode.get("season", 0)
        episode_num = episode.get("episode", 0)

        print(
            f"    Searching SubSource for: {series_title} "
            f"S{season:02d}E{episode_num:02d}"
        )

        queries = self._generate_episode_search_queries(episode)
        all_results = []

        for query in queries:
            try:
                print(f"      Trying query: {query}")

                # Use movie search with includeSeasons=True to get TV content
                search_url = f"{self.api_url}/movie/search"
                search_payload = {
                    "query": query,
                    "signal": {},
                    "includeSeasons": True,  # Include TV shows
                    "limit": 15,
                }

                response = self.session.post(
                    search_url, json=search_payload, timeout=15
                )
                response.raise_for_status()

                time.sleep(2)  # Rate limiting

                search_data = response.json()
                search_results = search_data.get("results", [])

                print(f"      Found {len(search_results)} result(s)")

                # Look for both TV series and movies that might match
                for result in search_results:
                    result_title = result.get("title", "").lower()
                    series_title_lower = series_title.lower()

                    # Skip if title doesn't match series
                    if series_title_lower not in result_title:
                        continue

                    link = result.get("link", "")
                    if not link:
                        continue

                    # For TV series, we can't directly access episodes
                    # For movies/specials, we can access subtitles
                    if "/subtitles/" in link:
                        # This is a movie/special - get subtitles directly
                        subtitles_url = f"{self.api_url}{link}"
                        params = {"language": language.lower(), "sort_by_date": "false"}

                        time.sleep(2)  # Rate limiting

                        sub_response = self.session.get(
                            subtitles_url, params=params, timeout=15
                        )
                        sub_response.raise_for_status()

                        subtitles_data = sub_response.json()
                        if isinstance(subtitles_data, list):
                            subtitles = subtitles_data
                        else:
                            subtitles = subtitles_data.get("subtitles", [])

                        # Filter subtitles that match our episode
                        for subtitle in subtitles:
                            if self._is_subtitle_match(subtitle, episode):
                                subtitle["source_query"] = query
                                subtitle["source_link"] = link
                                all_results.append(subtitle)

                        matching_count = len(
                            [
                                s
                                for s in subtitles
                                if self._is_subtitle_match(s, episode)
                            ]
                        )
                        print(
                            f"      Found {matching_count} matching episode subtitles"
                        )

                    # For TV series links, we would need a different approach
                    # but SubSource doesn't provide episode-level access

            except requests.exceptions.RequestException as e:
                print(f"      Error searching with query '{query}': {e}")
                continue

        # Remove duplicates based on subtitle ID
        unique_results = []
        seen_ids = set()
        for result in all_results:
            sub_id = result.get("id")
            if sub_id and sub_id not in seen_ids:
                seen_ids.add(sub_id)
                unique_results.append(result)

        print(f"    Found {len(unique_results)} unique matching subtitles")

        if not unique_results:
            # Record failure for tracking
            episode_key = f"{series_title}:S{season:02d}E{episode_num:02d}"
            self.tracker.record_no_subtitles_found(episode_key, 0, language)

        return unique_results

    def download_subtitle(self, subtitle: Dict, filename: str) -> Optional[str]:
        """
        Download a subtitle file.

        Args:
            subtitle: Subtitle data from SubSource
            filename: Local filename for the subtitle

        Returns:
            Path to downloaded file or None if failed
        """
        # Reuse the movie downloader logic from subsource.py
        # This is the same download process
        from api.subsource import SubSourceDownloader

        # Create a temporary movie downloader to reuse download logic
        temp_downloader = SubSourceDownloader(
            self.api_url, self.download_dir, self.bazarr
        )
        return temp_downloader.download_subtitle(subtitle, filename)

    def get_subtitle_for_episode(self, episode: Dict) -> Tuple[List[str], int]:
        """
        Download subtitles for an episode.

        Args:
            episode: Episode dictionary from Bazarr API

        Returns:
            Tuple of (downloaded subtitle file paths, number of skipped subtitles)
        """
        series_title = episode.get("seriesTitle", "Unknown")
        season = episode.get("season", 0)
        episode_num = episode.get("episode", 0)
        missing_subs = episode.get("missing_subtitles", [])

        episode_key = f"{series_title}:S{season:02d}E{episode_num:02d}"

        downloaded_files = []
        skipped_count = 0

        print(f"  Processing: {episode_key}")

        for sub in missing_subs:
            lang_name = sub.get("name", "Unknown")
            lang_code = sub.get("code2", "en")

            print(f"    Looking for {lang_name} subtitle...")

            # Check if we should skip this search based on recent failures
            search_interval = self._get_search_interval_hours()
            if self.tracker.should_skip_search(
                episode_key, 0, lang_name.lower(), search_interval
            ):
                print(
                    f"    Skipping {lang_name} subtitle "
                    f"(last tried within {search_interval}h interval)"
                )
                skipped_count += 1
                continue

            # Search for subtitles
            results = self.search_episode_subtitles(episode, lang_name.lower())

            if not results:
                print(f"    No subtitles found for {lang_name}")
                continue

            # Take the best result (first one)
            best_result = results[0]

            # Download subtitle
            downloaded_file = self.download_subtitle(
                best_result, f"temp_episode_{lang_code}.srt"
            )
            if downloaded_file:
                downloaded_files.append(downloaded_file)
                print(f"    ✓ Downloaded {lang_name} subtitle")
            else:
                self.tracker.record_download_failure(
                    episode_key, 0, lang_name.lower(), "Download failed"
                )
                print(f"    ✗ Failed to download {lang_name} subtitle")

        return downloaded_files, skipped_count
