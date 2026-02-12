# --------------------
#  Market embed parser utility
# --------------------
import re
import time
from typing import Optional, Tuple

import discord

from constants.grand_line_auction_constants import KHY_USER_ID
from constants.rarity import (
    RARITY_MAP,
    get_rarity,
    is_mon_auctionable,
    is_mon_exclusive,
)
from utils.cache.cache_list import market_value_cache
from utils.db.market_value_db import (
    fetch_image_link_cache,
    fetch_market_value_cache,
    update_image_link,
    update_market_value_via_listener,
    fetch_pokemon_exclusivity_cache
)
from utils.essentials.minimum_increment import (
    compute_maximum_auction_duration_seconds,
    compute_minimum_increment,
    format_names_for_market_value_lookup,
)
from utils.logs.debug_log import debug_log, enable_debug
from utils.logs.pretty_log import pretty_log

from .price_data_listener import pink_check_react_if_khy

enable_debug(f"{__name__}.lookup_listener")


def extract_pokemon_name_before_hash(text):
    match = re.match(r"(.+?)\s*#", text)
    return match.group(1).strip() if match else text.strip()


# Extracts the dex number from a string like 'Wooper #194'. Returns an int or None.
def extract_dex_number(text):
    match = re.search(r"#(\d+)", text)
    return int(match.group(1)) if match else None


def extract_lowest_market_from_embed(embed) -> int | None:
    """Extracts the lowest market value from a Discord embed, ignoring emoji, and returns it as an int."""
    for field in embed.fields:
        if "Lowest Market" in field.name:
            # Remove emoji and extract the number
            import re

            cleaned_value = re.sub(r"<:[^>]+>", "", field.value)
            match = re.search(r"([\d,]+)", cleaned_value)
            if match:
                return int(match.group(1).replace(",", ""))
    return None


async def lookup_listener(bot, message: discord.Message):
    """Listens to mh lookup command outputs and updates market value cache accordingly."""
    embed = message.embeds[0] if message.embeds else None
    if not embed:
        return

    embed_title = embed.title if embed.title else ""
    pokemon_name = extract_pokemon_name_before_hash(embed_title)
    if not pokemon_name:
        debug_log(f"Could not extract pokemon name from embed title: '{embed_title}'")
        return
    embed_image_url = embed.image.url if embed.image else None
    image_link_cache = fetch_image_link_cache(pokemon_name)
    existing_exclusive_status = fetch_pokemon_exclusivity_cache(pokemon_name)
    is_exclusive = is_mon_exclusive(pokemon_name)
    if existing_exclusive_status != is_exclusive:
        new_exclusive = is_exclusive
    else:
        new_exclusive = existing_exclusive_status
    if embed_image_url and image_link_cache != embed_image_url:
        await update_image_link(bot, pokemon_name, embed_image_url, new_exclusive)
        debug_log(
            f"Updated image link for {pokemon_name} to {embed_image_url} based on mh lookup command output."
        )
        pretty_log(
            "info",
            f"Updated image link for {pokemon_name} to {embed_image_url} based on mh lookup command output.",
        )

    lowest_market = extract_lowest_market_from_embed(embed)
    if lowest_market is None:
        debug_log(f"Could not extract lowest market value from embed: '{embed_title}'")
        return
    debug_log(
        f"Extracted data from embed - Pokemon: '{pokemon_name}', Lowest Market: {lowest_market:,}"
    )
    current_time = int(time.time())
    formatted_name = format_names_for_market_value_lookup(pokemon_name)
    await update_market_value_via_listener(
        bot=bot,
        pokemon_name=formatted_name,
        lowest_market=lowest_market,
        listing_seen=str(current_time),
        image_link=embed_image_url,
    )
    pretty_log(
        "info",
        f"Updated market value for {formatted_name} to {lowest_market:,} based on mh lookup command output.",
    )
    await message.add_reaction("💗")
