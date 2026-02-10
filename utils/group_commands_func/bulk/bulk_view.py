import discord
from discord import app_commands
from discord.ext import commands

from constants.grand_line_auction_constants import DEFAULT_EMBED_COLOR
from utils.cache.auction_cache import get_auction_cache
from utils.logs.debug_log import debug_log, enable_debug
from utils.logs.pretty_log import pretty_log
from utils.visuals.pretty_defer import pretty_defer


async def bulk_view_func(
    bot: commands.Bot,
    interaction: discord.Interaction,
):
    """Views the details of the current bulk auction."""

    # Defer
    loader = await pretty_defer(
        interaction=interaction,
        content="Fetching bulk auction details...",
        ephemeral=False,
    )
    # Get auction details from cache
    auction = get_auction_cache(interaction.channel_id)
    if not auction:
        await loader.error(content="This channel does not have an active auction.")
        return
    is_bulk = auction.get("is_bulk", False)
    if not is_bulk:
        await loader.error(content="This channel does not have an active bulk auction.")
        return

    pokemon = auction.get("pokemon", None)
    if not pokemon:
        await loader.error(
            content="Could not retrieve Pokémon details for this auction."
        )
        return
    pokemon_list = pokemon.split(", ") if pokemon else []
    description = "\n".join(f"> - {p.title()}" for p in pokemon_list)

    content = f"💌 **Bulk Auction Details:**\n{description}"
    await loader.success(content=content, add_check_emoji=False)
