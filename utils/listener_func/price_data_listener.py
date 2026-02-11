# --------------------
#  Market embed parser utility
# --------------------
import re
import time
from typing import Optional, Tuple

import discord

from constants.grand_line_auction_constants import KHY_USER_ID
from utils.cache.cache_list import market_value_cache
from utils.db.market_value_db import update_image_link, update_market_value_via_listener
from utils.essentials.minimum_increment import (
    compute_maximum_auction_duration_seconds,
    compute_minimum_increment,
    format_names_for_market_value_lookup,
)
from utils.logs.debug_log import debug_log, enable_debug
from utils.logs.pretty_log import pretty_log

# enable_debug(f"{__name__}.price_data_listener")
# enable_debug(f"{__name__}.pink_check_react_if_khy")


async def pink_check_react_if_khy(message: discord.Message):
    """Adds a pink heart react to the message if the replied message author is Khy, to indicate that the price data listener has processed this message."""
    replied_message = None
    if message.reference:
        replied_message = message.reference.resolved
        if not replied_message and message.reference.message_id:
            try:
                replied_message = await message.channel.fetch_message(
                    message.reference.message_id
                )
                debug_log(
                    f"pink_check_react_if_khy: Fetched replied message for message.id={message.id}"
                )
            except Exception as e:
                debug_log(
                    f"pink_check_react_if_khy: Failed to fetch replied message for message.id={message.id}: {e}"
                )
    debug_log(
        f"pink_check_react_if_khy: message.id={message.id}, author.id={getattr(message.author, 'id', None)}, has_reference={bool(message.reference)}"
    )
    if not replied_message:
        debug_log(
            f"pink_check_react_if_khy: No replied message found for message.id={message.id}"
        )
        return

    # Check if the replied message author is KHY
    if getattr(replied_message.author, "id", None) == KHY_USER_ID:
        try:
            await message.add_reaction("💗")
            debug_log(
                f"Added pink heart reaction to message ID {message.id} for Khy's command."
            )
        except Exception as e:
            debug_log(f"Failed to add reaction to message ID {message.id}: {e}")
    else:
        debug_log(
            f"pink_check_react_if_khy: Replied message author is not Khy (author.id={getattr(replied_message.author, 'id', None)}) for message.id={message.id}"
        )
        return


def extract_pokemon_name_from_title(text):
    # Matches text after '>' and before 'Market Data'
    match = re.search(r">\s*(.*?)\s+Market Data", text)
    return match.group(1) if match else None


def extract_price_from_embed(embed: discord.Embed) -> Optional[int]:
    """Extracts the all-time avg price from a Discord embed field and returns it as an int, ignoring emoji IDs."""
    for field in embed.fields:
        if "All-time avg price" in field.name:
            # Remove emoji and IDs from the value
            # This removes patterns like <:PokeCoin:666879070650236928>
            cleaned_value = re.sub(r"<:[^>]+>", "", field.value)
            match = re.search(r"([\d,]+)", cleaned_value)
            if match:
                price_str = match.group(1).replace(",", "")
                return int(price_str)
    return None


async def price_data_listener(bot: discord.Client, message: discord.Message):
    """Listens to price data embeds"""
    embed = message.embeds[0] if message.embeds else None
    if not embed:
        return

    embed_title = embed.title or ""
    embed_image = embed.image.url if embed.image else ""
    pokemon_name = extract_pokemon_name_from_title(embed_title)
    if not pokemon_name:
        debug_log(f"Could not extract Pokémon name from embed title: {embed_title}")

    formatted_name = format_names_for_market_value_lookup(pokemon_name)
    if formatted_name in market_value_cache:
        # Update the image link in the cache if it's different from the existing one
        market_info = market_value_cache[formatted_name]
        existing_image_link = market_info.get("image_link")
        if embed_image and existing_image_link != embed_image:
            await update_image_link(bot, formatted_name, embed_image)

        debug_log(
            f"Market value for {formatted_name} already exists in cache. Skipping update."
        )
        return

    all_time_avg_price = extract_price_from_embed(embed)

    if all_time_avg_price is None:
        debug_log(f"Could not extract price from embed for Pokémon {pokemon_name}")
        return
    date_listed = int(time.time())
    await update_market_value_via_listener(
        bot,
        formatted_name,
        all_time_avg_price,
        str(date_listed),
        image_link=embed_image,
    )
    pretty_log(
        "info",
        f"Updated market value for {formatted_name} to {all_time_avg_price:,} based on new price data embed.",
    )
    await pink_check_react_if_khy(message)
