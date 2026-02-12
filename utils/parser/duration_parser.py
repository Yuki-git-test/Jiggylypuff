import re
import time
from datetime import timedelta

from constants.auction import (
    MAX_REGULAR_AUCTION_SECONDS,
    MAX_SPEED_AUCTION_SECONDS,
    MIN_REGULAR_AUCTION_SECONDS,
    MIN_SPEED_AUCTION_SECONDS,
)


def format_seconds(seconds: int) -> str:
    parts = []
    days, rem = divmod(seconds, 86400)
    hours, rem = divmod(rem, 3600)
    minutes, rem = divmod(rem, 60)

    # Handle exact multiples for cleaner output
    if days and hours == 0 and minutes == 0 and rem == 0:
        unit = "day" if days == 1 else "days"
        return f"{days} {unit}"
    if hours and minutes == 0 and rem == 0:
        unit = "hour" if hours == 1 else "hours"
        return f"{hours} {unit}"
    if minutes and rem == 0 and days == 0 and hours == 0:
        unit = "minute" if minutes == 1 else "minutes"
        return f"{minutes} {unit}"
    if rem and days == 0 and hours == 0 and minutes == 0:
        unit = "second" if rem == 1 else "seconds"
        return f"{rem} {unit}"

    # Otherwise, build composite string
    if days:
        unit = "day" if days == 1 else "days"
        parts.append(f"{days} {unit}")
    if hours:
        unit = "hour" if hours == 1 else "hours"
        parts.append(f"{hours} {unit}")
    if minutes:
        unit = "minute" if minutes == 1 else "minutes"
        parts.append(f"{minutes} {unit}")
    if rem:
        unit = "second" if rem == 1 else "seconds"
        parts.append(f"{rem} {unit}")
    return " and ".join(parts)


def parse_duration(
    duration_str: str, max_duration: int, is_speed_auc: bool = False
) -> tuple[str, int, int]:
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

    MIN_SECONDS = (
        MIN_SPEED_AUCTION_SECONDS if is_speed_auc else MIN_REGULAR_AUCTION_SECONDS
    )
    MAX_SECONDS = MAX_SPEED_AUCTION_SECONDS if is_speed_auc else max_duration
    # Minimum duration is 60 minutes
    if total_seconds < MIN_SECONDS:
        raise ValueError(f"Duration too short. Minimum is {MIN_SECONDS // 60} minutes.")

    # Maximum duration check
    if total_seconds > MAX_SECONDS:
        raise ValueError(f"Duration too long. Maximum is {MAX_SECONDS // 3600} hours.")

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
    return normalized_str, unix_end, MAX_SECONDS


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
