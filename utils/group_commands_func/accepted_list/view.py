import discord
from discord import app_commands
from discord.ext import commands

from constants.grand_line_auction_constants import DEFAULT_EMBED_COLOR
from utils.cache.auction_cache import get_auction_cache
from utils.logs.debug_log import debug_log, enable_debug
from utils.logs.pretty_log import pretty_log
from utils.visuals.pretty_defer import pretty_defer


async def view_accepted_list_func(
    bot: commands.Bot,
    interaction: discord.Interaction,
):
    """Views the accepted Pokémon list for the current auction."""

    # Defer
    loader = await pretty_defer(
        interaction=interaction,
        content="Fetching accepted Pokémon list...",
        ephemeral=True,
    )
    # Get auction details from cache
    auction = get_auction_cache(interaction.channel_id)
    if not auction:
        await loader.error(content="This channel does not have an active auction.")
        return
    accepted_list = auction.get("accepted_list", None)
    if not accepted_list:
        await loader.error(
            content="This auction does not have an accepted Pokémon list."
        )
        return
    accepted_list = f"- {accepted_list.replace(', ', '\n- ')}"
    embed = discord.Embed(
        title="Accepted Pokémon List",
        description=accepted_list,
        color=DEFAULT_EMBED_COLOR,
    )
    image_link = auction.get("image_link", None)
    if image_link:
        embed.set_thumbnail(url=image_link)
    await loader.success(content="", embed=embed)
