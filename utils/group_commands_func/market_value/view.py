import re
import time
from datetime import datetime

import discord
from discord import app_commands
from discord.ext import commands

from constants.grand_line_auction_constants import KHY_CHANNEL_ID
from constants.paldea_galar_dict import get_dex_number_by_name
from constants.rarity import RARITY_MAP, get_rarity, is_mon_auctionable
from utils.autocomplete.pokemon_autocomplete import (
    format_price_w_coin,
    pokemon_autocomplete,
)
from utils.db.auction_db import upsert_auction
from utils.db.market_value_db import fetch_market_value_cache
from utils.essentials.auction_broadcast import broadcast_auction
from utils.logs.debug_log import debug_log, enable_debug
from utils.logs.pretty_log import pretty_log
from utils.parser.duration_parser import parse_duration
from utils.parser.number_parser import parse_compact_number
from utils.visuals.get_pokemon_gif import get_pokemon_gif
from utils.visuals.pretty_defer import pretty_defer
from utils.essentials.minimum_increment import format_names_for_market_value_lookup

enable_debug(f"{__name__}.view_market_value_func")


# enable_debug(f"{__name__}.format_timestamp")


def format_timestamp(timestamp):
    """Converts timestamp to <t:TIMESTAMP:R> and <t:TIMESTAMP:d> format for Discord. if its in int already, if not extract the unix timestamp from the string and convert it."""
    debug_log(f"format_timestamp input: {timestamp!r}")
    if isinstance(timestamp, int):
        unix_timestamp = timestamp
        formatted = f"<t:{unix_timestamp}:f> - <t:{unix_timestamp}:R>"
        debug_log(
            f"format_timestamp int branch: unix_timestamp={unix_timestamp}, formatted={formatted}"
        )
        return formatted
    else:
        # Handle string that is just a number
        if isinstance(timestamp, str) and timestamp.isdigit():
            unix_timestamp = int(timestamp)
            formatted = f"<t:{unix_timestamp}:f> - <t:{unix_timestamp}:R>"
            debug_log(
                f"format_timestamp numeric str branch: unix_timestamp={unix_timestamp}, formatted={formatted}"
            )
            return formatted
        # Extract unix timestamp from the string <t:TIMESTAMP:R> or <t:TIMESTAMP:d> or any similar format
        match = re.search(r"<t:(\d+):[a-zA-Z]>", timestamp)
        if match:
            unix_timestamp = int(match.group(1))
            formatted = f"<t:{unix_timestamp}:f> - <t:{unix_timestamp}:R>"
            debug_log(
                f"format_timestamp str branch: unix_timestamp={unix_timestamp}, formatted={formatted}"
            )
            return formatted
        else:
            debug_log("format_timestamp: no valid timestamp found in string")
            return None


def strip_prefixes(pokemon_name: str):
    """
    Strip form prefixes from a Pokémon name to get the base name for market value lookup.
    Handles prefixes like "Shiny", "Mega", "Gigantamax", "Shiny Mega", etc.
    """
    prefixes = [
        "shiny mega",
        "shiny gigantamax",
        "golden mega",
        "gigantamax",
        "mega",
        "shiny",
        "golden",
    ]
    pokemon_name_lower = pokemon_name.lower()
    for prefix in prefixes:
        if pokemon_name_lower.startswith(prefix + " "):
            return pokemon_name[len(prefix) + 1 :].strip()
    return pokemon_name.strip()


async def view_market_value_func(
    bot: commands.Bot, interaction: discord.Interaction, pokemon: str
):
    """
    View the current market value for a specific Pokémon.
    Fetches data from cache and returns a formatted string with the information.
    """
    loader = await pretty_defer(
        interaction=interaction, content="Fetching market value...", ephemeral=False
    )

    # See what data we have in cache for this pokemon
    debug_log(f"Fetching market value for {pokemon} from cache")
    # show some sample data for debugging
    sample_data = fetch_market_value_cache(pokemon)

    if sample_data:
        debug_log(f"Sample market value cache data: {list(sample_data.items())[:5]}")
    else:
        debug_log("No market value cache data found for this Pokémon.")
    market_formatted_name = format_names_for_market_value_lookup(pokemon)
    pretty_log(
        "info", f"Formatted name for market value lookup: {market_formatted_name}"
    )
    if market_formatted_name is None:
        await loader.error("Could not parse Pokémon name for market value lookup.")
        return
    market_data = fetch_market_value_cache(market_formatted_name)
    if not market_data:
        await loader.error(
            f"No market data found for **{market_formatted_name.title()}**."
        )
        return

    lowest_market = market_data.get("lowest_market", "N/A")
    listing_seen = market_data.get("listing_seen", "N/A")
    image_link = market_data.get("image_link", None)
    if not image_link:
        image_link = get_pokemon_gif(pokemon)
    is_exclusive = market_data.get("is_exclusive", False)
    rarity = get_rarity(pokemon)
    rarity_emoji = RARITY_MAP.get(rarity, {}).get("emoji", "")
    dex = get_dex_number_by_name(pokemon)
    dex = str(dex) if dex is not None else "N/A"
    clean_name = strip_prefixes(market_formatted_name)
    formatted_pokemon = (
        f"{rarity_emoji} {clean_name.title()} (#{dex})"
        if rarity_emoji
        else f"{clean_name.title()} (#{dex})"
    )
    formatted_timestamp = format_timestamp(listing_seen)
    display_listing_seen = formatted_timestamp if formatted_timestamp else "N/A"

    if not is_exclusive:
        color = RARITY_MAP.get(rarity, {}).get("color", 0xFFFFFF)
    else:
        color = RARITY_MAP.get("exclusive", {}).get("color", 0xFFD700)
    embed = discord.Embed(
        title=f"Market Value Info",
        description=(
            f"- **Pokemon:** {formatted_pokemon}\n"
            f"- **Lowest Market Value:** {format_price_w_coin(lowest_market) if lowest_market != 'N/A' else 'N/A'}\n"
            f"- **Exclusive:** {'Yes' if is_exclusive else 'No'}\n"
            f"- **Last Listing Seen:** {display_listing_seen}"
        ),
        color=color,
    )
    if image_link:
        embed.set_thumbnail(url=image_link)
    await loader.success(embed=embed, content="")
