import discord
from discord import app_commands
from discord.ext import commands

from constants.grand_line_auction_constants import DEFAULT_EMBED_COLOR
from utils.cache.auction_cache import get_auction_cache
from utils.db.auction_db import remove_accepted_list
from utils.logs.debug_log import debug_log, enable_debug
from utils.logs.pretty_log import pretty_log
from utils.visuals.pretty_defer import pretty_defer


async def clear_accepted_list_func(
    bot: commands.Bot,
    interaction: discord.Interaction,
):
    """Clears the accepted Pokémon list for the current auction."""

    # Defer
    loader = await pretty_defer(
        interaction=interaction,
        content="Clearing accepted Pokémon list...",
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
            content="Only the auction host can clear the accepted Pokémon list."
        )
        return

    # Check if there's an accepted list to clear
    accepted_list = auction.get("accepted_list", None)
    if not accepted_list:
        await loader.error(
            content="This auction does not have an accepted Pokémon list to clear."
        )
        return

    # Clear accepted list in database
    try:
        await remove_accepted_list(bot, interaction.channel_id)
        await loader.success(content="Accepted Pokémon list has been cleared.")
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
