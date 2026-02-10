import re

import discord
from discord import app_commands

from constants.grand_line_auction_constants import GRAND_LINE_AUCTION_EMOJIS
from constants.weakness_chart import weakness_chart as WEAKNESS_CHART
from utils.logs.pretty_log import pretty_log


def format_price(n: int) -> str:
    """Format PokeCoin price into K/M shorthand."""
    if n >= 1_000_000:
        return f"{n/1_000_000:.1f}M"
    elif n >= 1_000:
        return f"{n/1_000:.1f}K"
    return str(n)


def shorten_format_price_w_coin(n: int) -> str:
    """Format PokeCoin price into K/M shorthand."""
    pokecoin = GRAND_LINE_AUCTION_EMOJIS.pokecoins
    if n >= 1_000_000:
        value = n / 1_000_000
        suffix = "M"
    elif n >= 1_000:
        value = n / 1_000
        suffix = "K"
    else:
        return f"{pokecoin} {n}"


def format_price_w_coin(n: int) -> str:
    """Format PokeCoin price with commas (no K/M shorthand)."""
    pokecoin = GRAND_LINE_AUCTION_EMOJIS.pokecoins
    return f"{pokecoin} {n:,}"


# ==================== 🗂 Build Weakness Indexes ==================== #
def build_weakness_indexes(weakness_chart: dict):
    dex_to_key = {}
    key_normalized = {}
    for key, data in weakness_chart.items():
        dex_raw = data.get("dex")
        try:
            dex_int = int(dex_raw) if dex_raw is not None else None
        except Exception:
            dex_int = None

        if dex_int is not None:
            dex_to_key[dex_int] = key

        norm = key.lower().replace("-", " ").replace("_", " ").strip()
        key_normalized[norm] = key
        simple = re.sub(r"[^\w\s]", "", norm)
        key_normalized[simple] = key

    return dex_to_key, key_normalized


DEX_TO_KEY, KEY_NORMALIZED = build_weakness_indexes(WEAKNESS_CHART)

# Pre-build clean list
POKEMON_LIST: list[tuple[str, int]] = [
    (key.title(), int(data.get("dex", 0)))
    for key, data in WEAKNESS_CHART.items()
    if data.get("dex") is not None
]

# ==================== 🐉 Unified Mega/Golden/Shiny Formatter ==================== #
POKEMON_NORMALIZED: list[tuple[str, str, int]] = []
for name, dex in POKEMON_LIST:
    norm = re.sub(r"[^\w\s]", "", name.lower()).replace(" ", "")
    POKEMON_NORMALIZED.append((name, norm, dex))


def old_format_display_name(raw_name: str) -> str:
    """
    Clean up Pokemon display names for autocomplete:
    - Remove dash only for Mega forms (Mega-Abomasnow → Mega Abomasnow)
    - Capitalize properly
    - Keep golden/shiny prefixes untouched
    - Handle special cases like Jangmo-o
    """
    SPECIAL_CASES = {
        "jangmo-o": "Jangmo-o",
        "hakamo-o": "Hakamo-o",
        "kommo-o": "Kommo-o",
        "tapu-koko": "Tapu-Koko",
        "tapu-lele": "Tapu-Lele",
        "tapu-bulu": "Tapu-Bulu",
        "tapu-fini": "Tapu-Fini",
    }

    clean_name = raw_name.lower()

    # Handle Mega form
    if "mega-" in clean_name:
        clean_name = clean_name.replace("mega-", "mega ")

    # Special case check
    if clean_name in SPECIAL_CASES:
        return SPECIAL_CASES[clean_name]

    # Capitalize all words
    display_name = " ".join(word.capitalize() for word in clean_name.split())

    return display_name


def format_display_name(raw_name: str) -> str:
    """
    Clean up Pokemon display names for autocomplete:
    - Remove dash only for Mega forms (Mega-Abomasnow → Mega Abomasnow)
    - Capitalize properly
    - Keep golden/shiny prefixes untouched
    - Handle special cases like Jangmo-o
    """
    SPECIAL_CASES = {
        "jangmo-o": "Jangmo-o",
        "hakamo-o": "Hakamo-o",
        "kommo-o": "Kommo-o",
        "tapu-koko": "Tapu-Koko",
        "tapu-lele": "Tapu-Lele",
        "tapu-bulu": "Tapu-Bulu",
        "tapu-fini": "Tapu-Fini",
    }

    clean_name = raw_name.lower()

    # Handle Mega form
    if "mega-" in clean_name:
        clean_name = clean_name.replace("mega-", "mega ")

    # Special case check
    if clean_name in SPECIAL_CASES:
        return SPECIAL_CASES[clean_name]

    # Handle shiny/golden prefixes
    for prefix in ["shiny ", "golden "]:
        if clean_name.startswith(prefix):
            rest = clean_name[len(prefix) :]
            # Capitalize after dashes and spaces
            rest = "-".join(
                " ".join(word.capitalize() for word in part.split())
                for part in rest.split("-")
            )
            return f"{prefix.capitalize()}{rest}"

    # Capitalize after dashes and spaces for all names
    display_name = "-".join(
        " ".join(word.capitalize() for word in part.split())
        for part in clean_name.split("-")
    )
    return display_name


# ==================== 🔍 Pokemon Autocomplete ==================== #
async def pokemon_autocomplete(
    interaction: discord.Interaction, current: str
) -> list[app_commands.Choice[str]]:
    """
    Autocomplete Pokemon names with #Dex display.
    Matches both names and dex numbers.
    """
    current_simple = re.sub(r"[^\w\s]", "", (current or "").lower()).replace(" ", "")
    results: list[app_commands.Choice[str]] = []
    seen = set()

    # Check if input looks numeric (dex search)
    dex_query = None
    if current_simple.isdigit():
        try:
            dex_query = int(current_simple)
        except ValueError:
            dex_query = None

    for name, norm, dex in POKEMON_NORMALIZED:
        # Match by name
        if not current_simple or current_simple in norm:
            display_name = format_display_name(name)
            display = f"{display_name} #{dex}"
            if display not in seen:
                results.append(app_commands.Choice(name=display, value=name))
                seen.add(display)

        # Match by dex number
        if dex_query is not None and dex_query == dex:
            display_name = format_display_name(name)
            display = f"{display_name} #{dex}"
            if display not in seen:
                results.append(app_commands.Choice(name=display, value=name))
                seen.add(display)

        if len(results) >= 25:
            break

    if not results:
        results.append(
            app_commands.Choice(name="No matches found", value=current or "")
        )

    return results
