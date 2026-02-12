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
    fetch_lowest_market_value_cache,
    fetch_pokemon_exclusivity_cache,
    update_image_link,
    update_market_value_via_listener,
    upsert_image_link,
)
from utils.essentials.minimum_increment import (
    compute_maximum_auction_duration_seconds,
    compute_minimum_increment,
    format_names_for_market_value_lookup,
)
from utils.logs.debug_log import debug_log, enable_debug
from utils.logs.pretty_log import pretty_log

from .mh_lookup_listener import extract_pokemon_name_before_hash

enable_debug(f"{__name__}.dex_listener")


async def dex_listener(bot, message: discord.Message):
    """Listens to dex command and updates the image link in the market value cache if it differs from the one in the command output."""
    embed = message.embeds[0] if message.embeds else None
    if not embed:
        return

    embed_title = embed.title if embed.title else ""
    embed_author_name = embed.author.name if embed.author else ""
    pokemon_name = extract_pokemon_name_before_hash(embed_author_name)
    if not pokemon_name:
        debug_log(
            f"Could not extract pokemon name from embed title: '{embed_author_name}'"
        )
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
        await upsert_image_link(bot, pokemon_name, embed_image_url, new_exclusive)
        debug_log(
            f"Updated image link for {pokemon_name} to {embed_image_url} based on mh lookup command output."
        )
        pretty_log(
            "info",
            f"Updated image link for {pokemon_name} to {embed_image_url} based on mh lookup command output.",
        )
