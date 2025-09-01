#!/usr/bin/env python3
"""
Bazarr Wanted Movies - SubSource Downloader

This script connects to your Bazarr instance, lists all movies that are missing
subtitles (wanted movies), and optionally downloads missing subtitles from
SubSource and uploads them to Bazarr.

Note: Parts of this codebase were generated with AI assistance but have been
thoroughly reviewed and validated by humans.

Features:
- Lists all movies missing subtitles from Bazarr
- Downloads subtitles from SubSource for each wanted movie
- Automatically uploads downloaded subtitles to Bazarr
- Supports multiple languages, forced, and hearing impaired subtitles
- Cleans up local files after successful upload

Usage:
    python run.py

Configuration:
    Edit the configuration variables below with your settings:
    - BAZARR_URL: Your Bazarr instance URL
    - API_KEY: Your Bazarr API key
    - BASIC_AUTH_USERNAME/PASSWORD: Basic auth credentials if required
    - SUBSOURCE_BASE_URL: SubSource website URL
    - DOWNLOAD_DIRECTORY: Local directory for temporary subtitle files
"""

import logging
import os
import sys
import time

from api.bazarr import Bazarr
from api.subsource import SubSourceDownloader
from core.config import load_config, setup_logging
from utils import format_movie_info

# Logging will be configured after loading config
logger = None


def main():
    """Main function to list wanted movies and download subtitles."""
    global logger

    try:
        # Load configuration first
        config = load_config()

        # Setup logging
        setup_logging(config["log_level"], config["log_file"])
        logger = logging.getLogger(__name__)

        # Log execution start for cron monitoring
        logger.info("=" * 60)
        logger.info("Starting Bazarr SubSource execution")
        logger.info("=" * 60)

        print("Bazarr Wanted Movies - SubSource Downloader")
        print("=" * 50)

        print(f"Connecting to Bazarr at: {config['bazarr_url']}")
        print("Fetching wanted movies...", end=" ", flush=True)

        # Initialize Bazarr client
        bazarr = Bazarr(
            config["bazarr_url"],
            config["api_key"],
            config["username"],
            config["password"],
        )

        # Fetch wanted movies
        data = bazarr.get_wanted_movies()
        if data is None:
            sys.exit(1)

        # Extract movies from response
        movies = data.get("data", [])

        print(f"Done!\nFound {len(movies)} wanted movies")

        if not movies:
            print("No movies are currently missing subtitles!")
            return

        print("\nWanted Movies:")
        print("-" * 40)

        # Display each movie
        for movie in movies:
            print(format_movie_info(movie))

        print(f"\nTotal: {len(movies)} movies need subtitles")

        # Automatically proceed with downloading subtitles
        print("\n" + "=" * 50)
        print("Automatically downloading missing subtitles from SubSource...")

        # Initialize SubSource downloader
        print("\nInitializing SubSource downloader...")
        downloader = SubSourceDownloader(
            config["subsource_api_url"],
            config["download_directory"],
            bazarr,  # Pass Bazarr client for API calls
        )

        print(f"Download directory: {config['download_directory']}")

        # Clean up obsolete tracking entries
        print("Cleaning up obsolete tracking entries...")
        removed_count = downloader.tracker.cleanup_obsolete_movies(movies)
        if removed_count > 0:
            print(f"Removed {removed_count} obsolete movie(s) from tracking database")

        print("\nStarting subtitle downloads...")
        print("=" * 50)

        total_downloads = 0
        successful_uploads = 0
        subtitles_skipped = 0

        # Process each movie
        for i, movie in enumerate(movies, 1):
            print(f"\n[{i}/{len(movies)}] Processing movie:")

            # Download subtitles for this movie
            downloaded_files, movie_skipped = downloader.get_subtitle_for_movie(movie)
            subtitles_skipped += movie_skipped

            if not downloaded_files:
                print("  No subtitles downloaded for this movie.")
                continue

            total_downloads += len(downloaded_files)

            # Get movie info for upload
            radarr_id = movie.get("radarrId", movie.get("radarrid"))
            if not radarr_id:
                print("  ✗ No Radarr ID found, cannot upload to Bazarr")
                continue

            # Upload each downloaded subtitle to Bazarr
            print("  Uploading subtitles to Bazarr...")
            missing_subs = movie.get("missing_subtitles", [])

            for j, subtitle_file in enumerate(downloaded_files):
                if j < len(missing_subs):
                    sub_info = missing_subs[j]
                    lang_code = sub_info.get("code2", "en")
                    forced = sub_info.get("forced", False)
                    hi = sub_info.get("hi", False)

                    if bazarr.upload_subtitle_to_bazarr(
                        radarr_id, subtitle_file, lang_code, forced, hi
                    ):
                        successful_uploads += 1

                        # Clean up tracking database for successful download
                        title = movie.get("title", "Unknown")
                        year = movie.get("year", 0)
                        lang_name = sub_info.get("name", "Unknown")
                        downloader.tracker.remove_successful_download(
                            title, year, lang_name.lower()
                        )

                        # Remove local file after successful upload
                        try:
                            os.remove(subtitle_file)
                            print(f"    Cleaned up local file: {subtitle_file}")
                        except OSError:
                            pass

            # Small delay between movies
            if i < len(movies):
                time.sleep(1)

        # Summary
        print("\n" + "=" * 50)
        print("DOWNLOAD SUMMARY")
        print("=" * 50)
        print(f"Movies processed: {len(movies)}")
        print(f"Subtitles downloaded: {total_downloads}")
        print(f"Subtitles uploaded to Bazarr: {successful_uploads}")
        print(f"Subtitles skipped: {subtitles_skipped}")

        if successful_uploads > 0:
            print(f"\n✓ Successfully processed {successful_uploads} subtitle(s)!")
            print("Check your Bazarr interface to verify the subtitles were added.")
            logger.info(
                f"Execution completed successfully. "
                f"{successful_uploads} subtitles uploaded."
            )
        else:
            print("\n⚠ No subtitles were successfully uploaded.")
            print("Check the messages above for details.")
            logger.warning("Execution completed with no successful uploads.")

        logger.info("=" * 60)
        logger.info("Bazarr SubSource execution finished")
        logger.info("=" * 60)

    except KeyboardInterrupt:
        error_msg = "Execution interrupted by user"
        print(f"\n{error_msg}")
        if logger:
            logger.info(error_msg)
        sys.exit(0)
    except Exception as e:
        error_msg = f"Fatal error during execution: {e}"
        print(f"\n❌ {error_msg}")
        if logger:
            logger.error(error_msg, exc_info=True)
        else:
            # If logging isn't set up yet, write to stderr for cron
            import traceback

            print(f"Stack trace:\n{traceback.format_exc()}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
