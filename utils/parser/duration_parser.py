import re
import time
from datetime import timedelta


def parse_duration(duration_str: str, max_duration: int) -> tuple[str, int]:
    """
    Parses a duration string like:
    - "3d"
    - "3 days"
    - "4d12h"
    - "4 days 12 hours"

    Returns:
        normalized_str (str): e.g. "3 days 12 hours"
        unix_end (int): current_time + duration in seconds

    Raises:
        ValueError: If invalid format or less than 1 day.
    """
    # Normalize for matching
    duration_str = duration_str.lower().replace(" ", "")

    # Match patterns like 4d, 4days, 4d12h, 4days12hours, 30m, 1h30m, etc.
    match = re.fullmatch(
        r"(?:(\d+)\s*d(?:ays?)?)?"  # days
        r"(?:(\d+)\s*h(?:ours?)?)?"  # hours
        r"(?:(\d+)\s*m(?:inutes?)?)?",  # minutes
        duration_str,
    )
    if not match:
        raise ValueError(
            "Invalid format. Examples: `3d`, `3 days`, `4d12h`, `4 days 12 hours`, `30m`, `1h30m`"
        )

    days = int(match.group(1)) if match.group(1) else 0
    hours = int(match.group(2)) if match.group(2) else 0
    minutes = int(match.group(3)) if match.group(3) else 0

    total_seconds = timedelta(days=days, hours=hours, minutes=minutes).total_seconds()

    # Minimum duration is 60 minutes
    if total_seconds < 3_600:
        raise ValueError("Minimum duration is **1 hour**.")

    # Maximum duration check
    if total_seconds > max_duration:
        raise ValueError(
            f"Duration too long. Maximum is {max_duration // 3600} hours."
        )

    # Create human-readable normalized string
    parts = []
    if days:
        parts.append(f"{days} day{'s' if days != 1 else ''}")
    if hours:
        parts.append(f"{hours} hour{'s' if hours != 1 else ''}")
    if minutes:
        parts.append(f"{minutes} minute{'s' if minutes != 1 else ''}")
    normalized_str = " ".join(parts)

    unix_end = int(time.time() + total_seconds)
    return normalized_str, unix_end

def parse_total_seconds(duration_str: str) -> int:
    """Parses a duration string and returns total seconds."""
    # Normalize for matching
    duration_str = duration_str.lower().replace(" ", "")

    # Match patterns like 4d, 4days, 4d12h, 4days12hours, 30m, 1h30m, etc.
    match = re.fullmatch(
        r"(?:(\d+)\s*d(?:ays?)?)?"  # days
        r"(?:(\d+)\s*h(?:ours?)?)?"  # hours
        r"(?:(\d+)\s*m(?:inutes?)?)?",  # minutes
        duration_str,
    )
    if not match:
        raise ValueError(
            "Invalid format. Examples: `3d`, `3 days`, `4d12h`, `4 days 12 hours`, `30m`, `1h30m`"
        )

    days = int(match.group(1)) if match.group(1) else 0
    hours = int(match.group(2)) if match.group(2) else 0
    minutes = int(match.group(3)) if match.group(3) else 0

    total_seconds = timedelta(days=days, hours=hours, minutes=minutes).total_seconds()
    return int(total_seconds)