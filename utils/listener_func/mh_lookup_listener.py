# --------------------
#  Market embed parser utility
# --------------------
import re
import time
from typing import Optional, Tuple

import discord

from constants.grand_line_auction_constants import KHY_USER_ID
from utils.cache.cache_list import market_value_cache
from utils.db.market_value_db import update_market_value_via_listener
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
    )
    pretty_log(
        "info",
        f"Updated market value for {formatted_name} to {lowest_market:,} based on mh lookup command output.",
    )
    await message.add_reaction("💗")
