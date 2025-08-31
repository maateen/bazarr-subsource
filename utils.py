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
    # Try different possible year field names
    year = (
        movie.get("year")
        or movie.get("movie_year")
        or movie.get("releaseYear")
        or movie.get("release_year")
    )
    missing_subs = movie.get("missing_subtitles", [])

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

    # Include year if available
    if year:
        return f"• {title} ({year}) - Missing: {missing_langs}"
    else:
        return f"• {title} - Missing: {missing_langs}"
