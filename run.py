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

        # Process movies if enabled
        movies = []
        if config.get("movies_enabled", True):
            # Fetch wanted movies
            data = bazarr.get_wanted_movies()
            if data is None:
                sys.exit(1)

            # Extract movies from response
            movies = data.get("data", [])

            print(f"Done!\nFound {len(movies)} wanted movies")

            if not movies:
                print("No movies are currently missing subtitles!")
        else:
            print("Movie processing disabled in configuration.")

        # Continue with movie processing if we have movies
        if movies:
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
                print(
                    f"Removed {removed_count} obsolete movie(s) from tracking database"
                )

            print("\nStarting subtitle downloads...")
            print("=" * 50)

        # Initialize counters (outside if block for summary)
        total_downloads = 0
        successful_uploads = 0
        subtitles_skipped = 0

        # Process movies if we have them
        if movies:
            # Process each movie
            for i, movie in enumerate(movies, 1):
                print(f"\n[{i}/{len(movies)}] Processing movie:")

                # Download subtitles for this movie
                downloaded_files, movie_skipped = downloader.get_subtitle_for_movie(
                    movie
                )
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

        # Process TV show episodes if enabled
        episodes_processed = 0
        episodes_downloads = 0
        episodes_uploads = 0
        episodes_skipped = 0

        if config.get("episodes_enabled", True):
            print("\n" + "=" * 50)
            print("PROCESSING TV SHOW EPISODES")
            print("=" * 50)

            from api.bazarr_episodes import BazarrEpisodeClient
            from api.tv_shows import TVShowSubSourceDownloader

            # Initialize episode clients
            episode_client = BazarrEpisodeClient(
                config["bazarr_url"],
                config["api_key"],
                config["username"],
                config["password"],
            )

            tv_downloader = TVShowSubSourceDownloader(
                config["subsource_api_url"],
                config["download_directory"],
                episode_client,
            )

            # Get wanted episodes
            episodes = episode_client.get_wanted_episodes()
            episodes_processed = len(episodes)

            if not episodes:
                print("No episodes want subtitles.")
            else:
                print(f"Found {len(episodes)} episode(s) wanting subtitles")

                # Clean up obsolete episode tracking entries
                print("Cleaning up obsolete episode tracking entries...")
                removed_count = tv_downloader.tracker.cleanup_obsolete_movies(episodes)
                if removed_count > 0:
                    print(
                        f"Removed {removed_count} obsolete episode(s) "
                        f"from tracking database"
                    )

                for i, episode in enumerate(episodes, 1):
                    print(f"\n[{i}/{len(episodes)}] Processing episode...")

                    # Download subtitles for this episode
                    downloaded_files, skipped_count = (
                        tv_downloader.get_subtitle_for_episode(episode)
                    )
                    episodes_downloads += len(downloaded_files)
                    episodes_skipped += skipped_count

                    # Upload each downloaded subtitle to Bazarr
                    for subtitle_file in downloaded_files:
                        # Extract subtitle info from the episode and file
                        series_id = episode.get("sonarrSeriesId") or episode.get(
                            "seriesId"
                        )
                        episode_id = episode.get("sonarrEpisodeId") or episode.get(
                            "episodeId"
                        )

                        # Determine language from filename or default to first
                        # missing subtitle
                        missing_subs = episode.get("missing_subtitles", [])
                        if missing_subs:
                            lang_code = missing_subs[0].get("code2", "en")
                            lang_name = missing_subs[0].get("name", "Unknown")
                        else:
                            lang_code = "en"
                            lang_name = "English"

                        if series_id and episode_id:
                            sub_info = {"name": lang_name, "code2": lang_code}

                            # Upload to Bazarr
                            if episode_client.upload_episode_subtitle(
                                series_id, episode_id, lang_code, subtitle_file
                            ):
                                episodes_uploads += 1
                                print(f"    ✓ Uploaded {lang_name} subtitle to Bazarr")

                                # Clean up tracking database for successful download
                                series_title = episode.get("seriesTitle", "Unknown")
                                season = episode.get("season", 0)
                                episode_num = episode.get("episode", 0)
                                episode_key = (
                                    f"{series_title}:S{season:02d}E{episode_num:02d}"
                                )
                                tv_downloader.tracker.remove_successful_download(
                                    episode_key, 0, lang_name.lower()
                                )

                                # Remove local file after successful upload
                                try:
                                    os.remove(subtitle_file)
                                    print(f"    Cleaned up local file: {subtitle_file}")
                                except OSError:
                                    pass
                            else:
                                print(
                                    f"    ✗ Failed to upload {lang_name} "
                                    f"subtitle to Bazarr"
                                )
                        else:
                            print("    ✗ Missing series_id or episode_id for upload")

                    # Small delay between episodes
                    if i < len(episodes):
                        time.sleep(1)

        # Summary
        print("\n" + "=" * 50)
        print("DOWNLOAD SUMMARY")
        print("=" * 50)
        print(f"Movies processed: {len(movies)}")
        print(f"Episodes processed: {episodes_processed}")
        print(f"Movie subtitles downloaded: {total_downloads}")
        print(f"Episode subtitles downloaded: {episodes_downloads}")
        print(f"Movie subtitles uploaded to Bazarr: {successful_uploads}")
        print(f"Episode subtitles uploaded to Bazarr: {episodes_uploads}")
        print(f"Movie subtitles skipped: {subtitles_skipped}")
        print(f"Episode subtitles skipped: {episodes_skipped}")

        total_all_uploads = successful_uploads + episodes_uploads

        if total_all_uploads > 0:
            print(f"\n✓ Successfully processed {total_all_uploads} subtitle(s)!")
            if successful_uploads > 0:
                print(f"  - Movies: {successful_uploads}")
            if episodes_uploads > 0:
                print(f"  - Episodes: {episodes_uploads}")
            print("Check your Bazarr interface to verify the subtitles were added.")
            logger.info(
                f"Execution completed successfully. "
                f"{total_all_uploads} subtitles uploaded "
                f"({successful_uploads} movies, {episodes_uploads} episodes)."
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
