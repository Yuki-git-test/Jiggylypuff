# --------------------
#  Market embed parser utility
# --------------------
import re
from typing import Optional, Tuple

import discord

from constants.rarity import (
    RARITY_MAP,
    get_rarity,
    is_mon_auctionable,
    is_mon_exclusive,
)
from utils.db.market_value_db import (
    fetch_pokemon_exclusivity_cache,
    update_market_value_via_listener,
)
from utils.logs.debug_log import debug_log, enable_debug
from utils.logs.pretty_log import pretty_log

from .price_data_listener import pink_check_react_if_khy

# enable_debug(f"{__name__}.market_view_listener")
# enable_debug(f"{__name__}.parse_first_market_listing")


def extract_pokemon_name_from_author(author_name: str) -> str | None:
    """
    Extract the Pokémon name from the embed author string.
    Example: 'PokeMeow Global Market — Mega Mewtwo Y Listings' → 'Mega Mewtwo Y'
    Returns the name between the last '—' (or '-') and 'Listings'.
    Returns None if not found.
    """
    # Try em dash first, then hyphen
    import re

    match = re.search(r"[—-]\s*(.*?)\s+Listings", author_name)
    if match:
        return match.group(1).strip().lower()
    return None


def parse_first_market_listing(
    embed_description: str,
) -> Optional[Tuple[str, int, int]]:
    """
    Parse the first listing from a PokeMeow market embed description.
    Returns (pokemon_name, price_each, date_listed) or None if not found.
    """

    # Regex to capture emojis and pokemon name
    listing_pattern = re.compile(
        r"`\d+\.\`?"
        r"\s*"
        r"((?:<:[^>]+>\s*)+)"  # group 1: all emojis before name
        r"\*\*(.*?)\*\*"  # group 2: pokemon name
        r"\s*•\s*"
        r"`#[^`]+`"
        r"\s*•\s*"
        r"<:PokeCoin:[^>]+>\s*"
        r"([\d,]+)"  # group 3: price
        r"\s*•.*?"
        r"<t:(\d+):d>"  # group 4: date
    )

    # Map emoji keywords to form prefixes (lowercase)
    form_map = [
        ("shinygigantamax", "Shiny Gigantamax"),
        ("shinymega", "Shiny Mega"),
        ("gigantamax", "Gigantamax"),
        ("mega", "Mega"),
        ("shiny", "Shiny"),
        ("golden mega", "Golden Mega"),
        ("golden", "Golden"),
    ]
    rarity_emojis = ["common", "uncommon", "rare", "superrare", "legendary"]

    for idx, line in enumerate(embed_description.splitlines()):
        debug_log(f"Parsing line {idx}: {line}")
        match = listing_pattern.search(line)
        if match:
            debug_log(f"Regex matched line {idx}: {line}")
            emoji_block = match.group(1)  # all emojis before name
            pokemon_name = match.group(2)
            price_each = int(match.group(3).replace(",", ""))
            date_listed = int(match.group(4))

            # Extract emoji names
            emoji_names = []
            for e in re.findall(r"<:([^:>]+):[0-9]+>", emoji_block):
                parts = e.split(":")
                if len(parts) > 1:
                    emoji_names.append(parts[1].lower())
                else:
                    emoji_names.append(parts[0].lower())
            debug_log(f"Emoji names found: {emoji_names}")

            # Remove rarity emojis
            filtered = [e for e in emoji_names if e not in rarity_emojis]

            # Build form prefix
            form_prefix = ""
            used = set()
            for form_key, form_label in form_map:
                # For multi-word forms, check if all words are present in order
                words = form_key.split()
                idxs = []
                last_idx = -1
                for w in words:
                    try:
                        i = filtered.index(w, last_idx + 1)
                        idxs.append(i)
                        last_idx = i
                    except ValueError:
                        break
                else:
                    # All words found in order
                    for i in idxs:
                        used.add(i)
                    if form_prefix:
                        form_prefix += " "
                    form_prefix += form_label
            # Add any single-word forms not already used
            for i, e in enumerate(filtered):
                if i in used:
                    continue
                for form_key, form_label in form_map:
                    if " " not in form_key and e == form_key:
                        if form_prefix:
                            form_prefix += " "
                        form_prefix += form_label
            full_name = f"{form_prefix} {pokemon_name}".strip()
            debug_log(f"Final parsed name: {full_name}")
            return (full_name, price_each, date_listed)

    debug_log("No regex match found in any line.")
    return None


async def market_view_listener(bot: discord.Client, message: discord.Message):
    """
    Listener function to process market view messages and update market values in the database.
    """
    debug_log("Entered market_view_listener.")
    embed = message.embeds[0] if message.embeds else None
    if not embed:
        debug_log("No embed found in the message.")
        return
    debug_log(f"Embed author: {getattr(embed.author, 'name', None)}")
    embed_description = embed.description or ""
    debug_log(
        f"Embed description: {embed_description[:200]}"
        + ("..." if len(embed_description) > 200 else "")
    )
    listing = parse_first_market_listing(embed_description)
    if listing:
        pokemon_name, price_each, date_listed = listing
        debug_log(
            f"Parsed market listing - Pokemon: {pokemon_name}, Price Each: {price_each}, Date Listed: {date_listed}"
        )
        pretty_log(
            tag="success",
            message=f"Updating market value for {pokemon_name} with price {price_each} listed at {date_listed}",
        )
        parsed_pokemon_name_from_author = extract_pokemon_name_from_author(
            embed.author.name
        )
        if not parsed_pokemon_name_from_author:
            debug_log("Could not extract Pokémon name from embed author.")
            return
        debug_log(
            f"Parsed Pokémon name from embed author: {parsed_pokemon_name_from_author}"
        )
        existing_exclusive_status = fetch_pokemon_exclusivity_cache(
            parsed_pokemon_name_from_author
        )
        is_exclusive = is_mon_exclusive(parsed_pokemon_name_from_author)
        if existing_exclusive_status != is_exclusive:
            new_exclusive = is_exclusive
        else:
            new_exclusive = existing_exclusive_status

        await update_market_value_via_listener(
            bot,
            parsed_pokemon_name_from_author,
            price_each,
            str(date_listed),
            is_exclusive=new_exclusive,
        )
        debug_log("Called update_market_value.")
        await pink_check_react_if_khy(message)
    else:
        debug_log("No valid market listing found in the embed description.")
    debug_log("Exiting market_view_listener.")
