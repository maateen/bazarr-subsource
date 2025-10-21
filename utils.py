"""
Utility functions for Bazarr SubSource integration.
"""

import logging
from typing import Dict

logger = logging.getLogger(__name__)


def format_movie_info(movie: Dict) -> str:
    """
    Format movie information for display.

    Args:
        movie: Movie dictionary from API response

    Returns:
        Formatted string with movie information
    """
    title = movie.get("title", "Unknown Title").strip()
    missing_subs = movie.get("missing_subtitles", [])

    # Get year from multiple possible fields
    year = (
        movie.get("year")
        or movie.get("movie_year")
        or movie.get("releaseYear")
        or movie.get("release_year")
    )

    # Format title with year if available
    if year:
        title_with_year = f"{title} ({year})"
    else:
        title_with_year = title

    # Format missing subtitles languages
    languages = []
    for sub in missing_subs:
        lang_name = sub.get("name", "Unknown")
        forced = sub.get("forced", False)
        hi = sub.get("hi", False)

        lang_desc = lang_name
        if forced:
            lang_desc += " (Forced)"
        if hi:
            lang_desc += " (HI)"

        languages.append(lang_desc)

    missing_langs = ", ".join(languages) if languages else "Unknown"

    return f"• {title_with_year} - Missing: {missing_langs}"


def format_episode_info(episode: Dict) -> str:
    """
    Format episode information for display.

    Args:
        episode: Episode dictionary from API response

    Returns:
        Formatted string with episode information
    """
    series_title = episode.get("series_title")
    season = episode.get("season")
    episode_number = episode.get("episode_number")
    episode_title = episode.get("episode_title")
    missing_subs = episode.get("missing_subtitles", [])

    # Format missing subtitles languages
    languages = []
    for sub in missing_subs:
        lang_name = sub.get("name", "Unknown")
        forced = sub.get("forced", False)
        hi = sub.get("hi", False)

        lang_desc = lang_name
        if forced:
            lang_desc += " (Forced)"
        if hi:
            lang_desc += " (HI)"

        languages.append(lang_desc)

    missing_langs = ", ".join(languages) if languages else "Unknown"

    # Format season and episode number
    if season is not None and episode_number is not None:
        season_episode = f"S{season}E{episode_number}"
    else:
        season_episode = "S??E??"

    return f"• {series_title} {season_episode} - {episode_title} - Missing: {missing_langs}"
