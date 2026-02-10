import re
from typing import Optional


# 💜────────────────────────────────────────────
#         [🤍 HELPER] Parse Compact Number
# 💜────────────────────────────────────────────
def parse_compact_number(raw_number: str) -> Optional[int]:
    """
    Converts human-friendly numbers (e.g. '1k', '1.1m', '1.2b', '1 000k') to int.
    Returns None if invalid.
    """

    if not isinstance(raw_number, str):
        return None

    # Normalize input
    raw_number = raw_number.strip().lower().replace(",", "").replace(" ", "")

    # Accept formats like 1.1k, 1000, 1.54m, 1.100k
    pattern = r"^(\d+(?:\.\d+)?)([kmb]?)$"
    match = re.fullmatch(pattern, raw_number)
    if not match:
        return None

    num_str, suffix = match.groups()

    try:
        number = float(num_str)
    except ValueError:
        return None

    # Apply suffix multiplier
    if suffix == "k":
        number *= 1_000
    elif suffix == "m":
        number *= 1_000_000
    elif suffix == "b":
        number *= 1_000_000_000

    # Safety range (avoid nonsense like 1e50)
    if number <= 0 or number > 10_000_000_000:
        return None

    return int(number)
