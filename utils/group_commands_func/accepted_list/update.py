import discord
from discord import app_commands
from discord.ext import commands

from constants.grand_line_auction_constants import DEFAULT_EMBED_COLOR
from utils.cache.auction_cache import get_auction_cache
from utils.db.auction_db import update_accepted_list
from utils.logs.debug_log import debug_log, enable_debug
from utils.logs.pretty_log import pretty_log
from utils.visuals.pretty_defer import pretty_defer


async def update_accepted_list_func(
    bot: commands.Bot,
    interaction: discord.Interaction,
    new_accepted_list: str,
):
    """Updates the accepted Pokémon list for the current auction."""

    # Defer
    loader = await pretty_defer(
        interaction=interaction,
        content="Updating accepted Pokémon list...",
        ephemeral=False,
    )
    # Get auction details from cache
    auction = get_auction_cache(interaction.channel_id)
    if not auction:
        await loader.error(content="This channel does not have an active auction.")
        return

    # Check if user is host  of the auction
    host_id = auction.get("host_id", None)
    if interaction.user.id != host_id:
        await loader.error(
            content="Only the auction host can update the accepted Pokémon list."
        )
        return

    # Check if there's an accepted list to clear
    accepted_list = auction.get("accepted_list", None)
    if not accepted_list:
        await loader.error(
            content="This auction does not have an accepted Pokémon list to update."
        )
        return

    # Update accepted list in database
    try:
        await update_accepted_list(bot, interaction.channel_id, new_accepted_list)
        content = f"💌 Accepted Pokémon list has been updated to:\n{new_accepted_list}"
        await loader.success(content=content)
    except Exception as e:
        pretty_log(
            tag="error",
            message=f"Error clearing accepted Pokémon list for channel ID {interaction.channel_id}: {e}",
            include_trace=True,
            bot=bot,
        )
        await loader.error(
            content="An error occurred while clearing the accepted Pokémon list. Please try again later."
        )
        return
