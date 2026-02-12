import re
import time
from datetime import datetime

import discord
from discord import app_commands
from discord.ext import commands

from constants.grand_line_auction_constants import KHY_CHANNEL_ID
from constants.paldea_galar_dict import get_dex_number_by_name
from constants.rarity import RARITY_MAP, get_rarity, is_mon_exclusive
from utils.autocomplete.pokemon_autocomplete import (
    format_price_w_coin,
    pokemon_autocomplete,
)
from utils.db.market_value_db import (
    fetch_market_value_cache,
    fetch_pokemon_exclusivity_cache,
    update_image_link,
    update_is_exclusive,
    update_market_value,
)
from utils.essentials.auction_broadcast import broadcast_auction
from utils.logs.debug_log import debug_log, enable_debug
from utils.logs.pretty_log import pretty_log
from utils.parser.number_parser import parse_compact_number
from utils.visuals.get_pokemon_gif import get_pokemon_gif
from utils.visuals.pretty_defer import pretty_defer

from .view import strip_prefixes


async def update_market_value_func(
    bot: commands.Bot,
    interaction: discord.Interaction,
    pokemon: str,
    amount: str = None,
    is_pokemon_exclusive: bool = False,
    image_link: str = None,
):
    """Manually  updates the market value for a Pokémon. Only usable by auctioneers."""
    loader = await pretty_defer(
        interaction=interaction, content="Updating market value...", ephemeral=False
    )
    if not amount and not is_pokemon_exclusive and not image_link:
        await loader.error(
            content="You must provide at least one value to update. (amount , exclusivity or image link)"
        )
        return

    market_data = fetch_market_value_cache(pokemon)
    if not amount and not market_data:
        await loader.error(
            content="No existing market value found for this Pokémon. Please provide an amount to set an initial market value."
        )
        return

    if not image_link:
        if market_data and market_data.get("image_link"):
            image_link = market_data["image_link"]
        else:
            image_link = get_pokemon_gif(pokemon)

    rarity = get_rarity(pokemon)
    rarity_emoji = RARITY_MAP.get(rarity, {}).get("emoji", "")
    color = RARITY_MAP.get(rarity, {}).get("color", 0xFFFFFF)
    dex = get_dex_number_by_name(pokemon)
    dex = str(dex) if dex is not None else "N/A"
    clean_name = strip_prefixes(pokemon)

    is_exclusive = None
    if is_pokemon_exclusive:
        is_exclusive = True
    else:
        is_exclusive = market_data.get("is_exclusive", False) if market_data else False

    if is_exclusive:
        color = RARITY_MAP.get("exclusive", {}).get("color", color)
    formatted_pokemon = (
        f"{rarity_emoji} {clean_name.title()} (#{dex})"
        if rarity_emoji
        else f"{clean_name.title()} (#{dex})"
    )
    if amount:
        try:
            amount_value = parse_compact_number(amount)
        except ValueError:
            await loader.error(
                content="Invalid amount format. Please enter a valid number (e.g. '1k', '1.5m')."
            )
            return
    else:
        amount_value = market_data["lowest_market"] if market_data else "N/A"
    formatted_amount = (
        format_price_w_coin(amount_value) if isinstance(amount_value, int) else "N/A"
    )
    # Listing seen is current time unix seconds
    listing_seen = int(time.time())
    # Update in db
    try:
        if amount and is_pokemon_exclusive:
            await update_market_value(
                bot, pokemon, amount_value, str(listing_seen), image_link, is_exclusive
            )
        elif not amount and is_pokemon_exclusive:
            await update_is_exclusive(bot, pokemon, is_exclusive, image_link)

        elif amount and not is_pokemon_exclusive:
            existing_exclusive_status = fetch_pokemon_exclusivity_cache(pokemon)
            if existing_exclusive_status != is_exclusive:
                new_exclusive = is_exclusive
            else:
                new_exclusive = existing_exclusive_status
            await update_market_value(
                bot, pokemon, amount_value, str(listing_seen), image_link, new_exclusive
            )
        elif not amount and not is_pokemon_exclusive and image_link:
            await update_image_link(bot, pokemon, image_link)
    except Exception as e:
        debug_log(f"Error updating market value for {pokemon}: {e}")
        await loader.error(content="An error occurred while updating the market value.")
        return

    # Build embed
    embed = discord.Embed(
        title=f"Market Value Updated",
        description=(
            f"- **Pokemon:** {formatted_pokemon}\n"
            f"- **Market Value:** {formatted_amount}\n"
            f"- **Exclusive:** {'Yes' if is_exclusive else 'No'}\n"
            f"- **Last Listing Seen:** Just now"
        ),
        color=color,
    )
    if image_link:
        embed.set_thumbnail(url=image_link)
    embed.set_author(
        name=interaction.user.display_name, icon_url=interaction.user.display_avatar.url
    )
    await loader.success(content="", embed=embed)
