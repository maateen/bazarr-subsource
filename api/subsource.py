"""
SubSource API client for downloading subtitles.
"""

import json
import logging
import os
import time
import zipfile
from typing import Dict, List, Optional

import requests

from core.tracking import SubtitleTracker

logger = logging.getLogger(__name__)


class SubSourceDownloader:
    """SubSource subtitle downloader."""

    def __init__(self, api_url: str, download_dir: str, bazarr=None):
        self.api_url = api_url
        self.download_dir = download_dir
        self.session = requests.Session()
        self.tracker = SubtitleTracker()
        self.bazarr = bazarr
        self._search_interval_hours = None
        self._movie_years_cache = {}  # Cache movie years to avoid repeated API calls

        # Setup optimized session headers
        self.session.headers.update(
            {
                "User-Agent": (
                    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                    "AppleWebKit/537.36"
                ),
                "Accept": "application/json",
                "Content-Type": "application/json",
                "Connection": "keep-alive",
            }
        )

        # Create download directory if it doesn't exist
        os.makedirs(download_dir, exist_ok=True)

    def search_subtitles(
        self, title: str, year: int, language: str = "english"
    ) -> List[Dict]:
        """
        Search for subtitles on SubSource using the correct two-step API.

        Args:
            title: Movie title
            year: Movie year
            language: Subtitle language (default: english)

        Returns:
            List of subtitle results
        """
        try:
            # Step 1: Search for the movie
            print(f"    Searching SubSource for: {title} ({year})")

            search_url = f"{self.api_url}/movie/search"
            search_payload = {
                "query": title,
                "signal": {},
                "includeSeasons": False,
                "limit": 15,
            }

            response = self.session.post(search_url, json=search_payload, timeout=15)
            response.raise_for_status()

            # Add delay to avoid rate limiting
            time.sleep(2)

            search_data = response.json()
            search_results = search_data.get("results", [])
            print(f"    Found {len(search_results)} movie(s) in search")

            # Find the best matching movie by year
            best_movie = None
            for movie in search_results:
                movie_year = movie.get("releaseYear")
                if movie_year == year:
                    best_movie = movie
                    break

            if not best_movie and search_results:
                # If no exact year match, take the first result
                best_movie = search_results[0]

            if not best_movie:
                print("    No matching movie found")
                self.tracker.record_no_subtitles_found(title, year, language)
                return []

            movie_link = best_movie.get("link")
            movie_title = best_movie.get("title", title)
            movie_year = best_movie.get("releaseYear", year)
            print(f"    Found movie: {movie_title} ({movie_year}) - link: {movie_link}")

            if not movie_link:
                print("    No movie link found")
                self.tracker.record_no_subtitles_found(title, year, language)
                return []

            # Step 2: Get subtitles for this movie using the link
            # The link is like "/subtitles/nightcrawler-2014", so we build the full URL
            subtitles_url = f"{self.api_url}{movie_link}"
            params = {"language": language.lower(), "sort_by_date": "false"}

            response = self.session.get(subtitles_url, params=params, timeout=15)
            response.raise_for_status()

            # Add delay to avoid rate limiting
            time.sleep(2)

            subtitles_data = response.json()

            # Handle different response formats
            if isinstance(subtitles_data, list):
                subtitles = subtitles_data
            else:
                subtitles = subtitles_data.get("subtitles", [])

            # Format results
            formatted_subtitles = []
            for subtitle in subtitles:
                subtitle_link = subtitle.get("link", "")
                subtitle_id = subtitle.get("id")
                subtitle_language = subtitle.get("language", language)

                # Build download URL from the link field (always use API)
                download_url = f"{self.api_url}/subtitle/{subtitle_id}/download"

                formatted_subtitles.append(
                    {
                        "id": subtitle_id,
                        "title": f"{movie_title} ({movie_year})",
                        "language": subtitle_language,
                        "download_url": download_url,
                        "filename": subtitle.get("release_info", ""),
                        "score": subtitle.get("rating", "unrated"),
                        "hearing_impaired": subtitle.get("hearing_impaired", 0),
                        "release_info": subtitle.get("release_info", ""),
                        "upload_date": subtitle.get("upload_date", ""),
                        "movie_link": movie_link,
                        "subtitle_link": subtitle_link,
                    }
                )

            print(f"    Found {len(formatted_subtitles)} {language} subtitle(s)")

            if not formatted_subtitles:
                self.tracker.record_no_subtitles_found(title, year, language)

            return formatted_subtitles

        except requests.exceptions.RequestException as e:
            print(f"    Error searching SubSource: {e}")
            self.tracker.record_no_subtitles_found(title, year, language)
            return []
        except (KeyError, ValueError) as e:
            print(f"    Error parsing SubSource response: {e}")
            self.tracker.record_no_subtitles_found(title, year, language)
            return []

    def download_subtitle(self, subtitle_info: Dict, filename: str) -> Optional[str]:
        """
        Download subtitle file from SubSource using the correct two-step process.
        SubSource downloads are always ZIP files that need to be extracted.

        Args:
            subtitle_info: Subtitle information dictionary
            filename: Local filename to save as

        Returns:
            Path to downloaded subtitle file or None if failed
        """
        subtitle_id = subtitle_info.get("id")
        subtitle_link = subtitle_info.get("subtitle_link", "")

        logger.info(f"Starting download for subtitle ID {subtitle_id}: {filename}")

        try:
            # Step 1: Get subtitle details to obtain download token
            if not subtitle_link:
                logger.error(f"No subtitle link found for subtitle ID {subtitle_id}")
                return None

            # Build subtitle details URL
            details_url = f"{self.api_url}/subtitle/{subtitle_link}"
            logger.info(f"Getting download token from: {details_url}")

            response = self.session.get(details_url, timeout=30)
            response.raise_for_status()

            # Add delay to avoid rate limiting
            time.sleep(2)

            details_data = response.json()
            subtitle_details = details_data.get("subtitle", {})
            download_token = subtitle_details.get("download_token")

            if not download_token:
                logger.error(
                    f"No download token found in response for subtitle ID "
                    f"{subtitle_id}"
                )
                logger.debug(f"Response data: {details_data}")
                return None

            logger.info(
                f"Got download token for subtitle ID {subtitle_id}: "
                f"{download_token[:20]}..."
            )

            # Step 2: Download using the token
            download_url = f"{self.api_url}/subtitle/download/{download_token}"
            logger.info(f"Downloading ZIP from: {download_url}")

            response = self.session.get(download_url, timeout=30)
            response.raise_for_status()

            # Add delay to avoid rate limiting
            time.sleep(2)

            # Check content type
            content_type = response.headers.get("content-type", "").lower()
            logger.debug(f"Download content-type: {content_type}")

            if "text/html" in content_type:
                logger.error(
                    f"Received HTML instead of ZIP file for subtitle ID "
                    f"{subtitle_id}"
                )
                return None

            # Save the ZIP file temporarily
            zip_filepath = os.path.join(self.download_dir, f"temp_{subtitle_id}.zip")

            with open(zip_filepath, "wb") as f:
                f.write(response.content)

            logger.info(
                f"Downloaded ZIP file: {zip_filepath} "
                f"(size: {len(response.content)} bytes)"
            )

            # Step 3: Extract and find the subtitle file
            extracted_file = self._extract_subtitle_from_zip(zip_filepath, subtitle_id)

            # Clean up ZIP file
            try:
                os.remove(zip_filepath)
                logger.debug(f"Cleaned up ZIP file: {zip_filepath}")
            except OSError as e:
                logger.warning(f"Could not clean up ZIP file {zip_filepath}: {e}")

            if extracted_file:
                logger.info(f"✓ Successfully extracted subtitle: {extracted_file}")
                return extracted_file
            else:
                logger.error(
                    f"✗ Failed to extract subtitle from ZIP for subtitle ID "
                    f"{subtitle_id}"
                )
                return None

        except requests.exceptions.RequestException as e:
            logger.error(f"HTTP error downloading subtitle ID {subtitle_id}: {e}")
            return None
        except (KeyError, ValueError) as e:
            logger.error(f"JSON parsing error for subtitle ID {subtitle_id}: {e}")
            return None
        except IOError as e:
            logger.error(f"File I/O error for subtitle ID {subtitle_id}: {e}")
            return None

    def _extract_subtitle_from_zip(
        self, zip_filepath: str, subtitle_id: int
    ) -> Optional[str]:
        """
        Extract subtitle file from ZIP archive, keeping original filename.
        Bazarr will handle renaming as needed.

        Args:
            zip_filepath: Path to the ZIP file
            subtitle_id: Subtitle ID for logging

        Returns:
            Path to extracted subtitle file or None if failed
        """
        try:
            logger.info(f"Extracting ZIP file: {zip_filepath}")

            with zipfile.ZipFile(zip_filepath, "r") as zip_ref:
                # List all files in the ZIP
                file_list = zip_ref.namelist()
                logger.debug(f"Files in ZIP: {file_list}")

                # Find subtitle files (common extensions)
                subtitle_extensions = [".srt", ".ass", ".ssa", ".sub", ".vtt", ".sbv"]
                subtitle_files = []

                for file in file_list:
                    file_lower = file.lower()
                    if any(file_lower.endswith(ext) for ext in subtitle_extensions):
                        subtitle_files.append(file)

                logger.info(
                    f"Found {len(subtitle_files)} subtitle file(s): {subtitle_files}"
                )

                if not subtitle_files:
                    logger.error(
                        f"No subtitle files found in ZIP for subtitle ID "
                        f"{subtitle_id}"
                    )
                    return None

                # Take the first subtitle file (or largest if multiple)
                if len(subtitle_files) > 1:
                    # Get file sizes and pick the largest one
                    largest_file = max(
                        subtitle_files, key=lambda f: zip_ref.getinfo(f).file_size
                    )
                    logger.info(
                        f"Multiple subtitle files found, selecting largest: "
                        f"{largest_file}"
                    )
                    selected_file = largest_file
                else:
                    selected_file = subtitle_files[0]

                # Extract the selected file with its original name
                logger.info(f"Extracting file: {selected_file}")

                # Use original filename from ZIP
                original_filename = os.path.basename(selected_file)
                target_path = os.path.join(self.download_dir, original_filename)

                # Extract directly to the target location
                zip_ref.extract(selected_file, self.download_dir)

                # If the extracted file is in a subdirectory, move it to the root
                extracted_path = os.path.join(self.download_dir, selected_file)
                if extracted_path != target_path:
                    os.rename(extracted_path, target_path)
                    # Clean up any empty directories
                    try:
                        parent_dir = os.path.dirname(extracted_path)
                        if parent_dir != self.download_dir:
                            os.rmdir(parent_dir)
                    except OSError:
                        pass  # Directory not empty or other issue

                file_size = os.path.getsize(target_path)
                logger.info(
                    f"Extracted subtitle to: {target_path} (size: {file_size} bytes)"
                )
                return target_path

        except zipfile.BadZipFile as e:
            logger.error(f"Invalid ZIP file {zip_filepath}: {e}")
            return None
        except (IOError, OSError) as e:
            logger.error(f"File error extracting from {zip_filepath}: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error extracting from {zip_filepath}: {e}")
            return None

    def get_subtitle_for_movie(self, movie: Dict) -> tuple[List[str], int]:
        """
        Download subtitles for a movie.

        Args:
            movie: Movie dictionary from Bazarr API

        Returns:
            Tuple of (downloaded subtitle file paths, number of skipped subtitles)
        """
        title = movie.get("title", "Unknown")
        year = self._get_movie_year(title, movie.get("year", 0))
        missing_subs = movie.get("missing_subtitles", [])

        downloaded_files = []
        skipped_count = 0

        print(f"  Processing: {title} ({year})")

        for sub in missing_subs:
            lang_name = sub.get("name", "Unknown")
            lang_code = sub.get("code2", "en")

            print(f"    Looking for {lang_name} subtitle...")

            # Check if we should skip this search based on recent failures
            # Use Bazarr's own search interval
            search_interval = self._get_search_interval_hours()
            if self.tracker.should_skip_search(
                title, year, lang_name.lower(), search_interval
            ):
                print(
                    f"    Skipping {lang_name} subtitle "
                    f"(last tried within {search_interval}h interval)"
                )
                skipped_count += 1
                continue

            # Search for subtitles
            results = self.search_subtitles(title, year, lang_name.lower())

            if not results:
                print(f"    No subtitles found for {lang_name}")
                continue

            # Take the best result (first one)
            best_result = results[0]

            # Download subtitle (keeping original filename from ZIP)
            downloaded_file = self.download_subtitle(
                best_result, f"temp_filename_{lang_code}.srt"
            )
            if downloaded_file:
                downloaded_files.append(downloaded_file)
                print(f"    ✓ Downloaded {lang_name} subtitle")
            else:
                self.tracker.record_download_failure(
                    title, year, lang_name.lower(), "Download failed"
                )
                print(f"    ✗ Failed to download {lang_name} subtitle")

            # Small delay to be respectful to the server
            time.sleep(0.5)

        return downloaded_files, skipped_count

    def _get_movie_year_from_bazarr(self, movie_title: str) -> Optional[int]:
        """
        Get movie year from Bazarr search API.

        Args:
            movie_title: Movie title to search for

        Returns:
            Movie year as integer or None if not found
        """
        if not self.bazarr:
            return None

        url = f"{self.bazarr.bazarr_url}/api/system/searches"
        params = {"query": movie_title}

        try:
            response = self.bazarr.session.get(
                url, params=params, auth=self.bazarr.auth, timeout=30
            )
            response.raise_for_status()
            search_data = response.json()

            # Handle different response formats - could be list or dict
            if isinstance(search_data, list):
                movies = search_data
            elif isinstance(search_data, dict):
                movies = search_data.get("movies", [])
            else:
                logger.warning(
                    f"Unexpected search response format: {type(search_data)}"
                )
                return None

            # Find the best matching movie by title
            for movie in movies:
                movie_title_result = movie.get("title", "").lower()
                if (
                    movie_title.lower() in movie_title_result
                    or movie_title_result in movie_title.lower()
                ):
                    year = movie.get("year")
                    if year:
                        logger.info(f"Found movie year for {movie_title}: {year}")
                        return int(year)

            # If no exact match, try the first result
            if movies:
                first_movie = movies[0]
                year = first_movie.get("year")
                if year:
                    logger.info(
                        f"Using first search result year for {movie_title}: {year}"
                    )
                    return int(year)

            logger.warning(f"No year found for movie {movie_title} in Bazarr search")
            return None

        except requests.exceptions.RequestException as e:
            logger.error(f"Error searching Bazarr for movie {movie_title}: {e}")
            return None
        except (json.JSONDecodeError, ValueError) as e:
            logger.error(f"Error parsing Bazarr search response for {movie_title}: {e}")
            return None

    def _get_movie_year(self, title: str, fallback_year: int = 0) -> int:
        """
        Get movie year from Bazarr search API or use cached value.

        Args:
            title: Movie title
            fallback_year: Year from wanted movies API (fallback)

        Returns:
            Movie year as integer
        """
        # Use fallback if we have a valid year
        if fallback_year and fallback_year > 1900:
            return fallback_year

        # Check cache first
        if title in self._movie_years_cache:
            return self._movie_years_cache[title]

        # Query Bazarr search API if client is available
        if self.bazarr:
            year = self._get_movie_year_from_bazarr(title)
            if year:
                self._movie_years_cache[title] = year
                return year

        # Use fallback or default
        final_year = fallback_year if fallback_year > 0 else 2000
        self._movie_years_cache[title] = final_year
        return final_year

    def _get_search_interval_hours(self) -> int:
        """
        Get the search interval from Bazarr or use cached value.

        Returns:
            Search interval in hours
        """
        if self._search_interval_hours is None:
            if self.bazarr:
                self._search_interval_hours = (
                    self.bazarr.get_missing_subtitles_search_interval()
                )
            else:
                logger.warning(
                    "No Bazarr client provided, using default 24 hour interval"
                )
                self._search_interval_hours = 24

        return self._search_interval_hours

    def get_tracking_summary(self) -> dict:
        """Get tracking summary statistics."""
        summary = self.tracker.get_tracking_summary()
        summary["search_interval_hours"] = self._get_search_interval_hours()
        return summary
