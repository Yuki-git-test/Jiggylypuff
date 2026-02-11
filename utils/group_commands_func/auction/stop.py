import time
from datetime import datetime

import discord
from discord import app_commands
from discord.ext import commands

from constants.aesthetic import Images
from constants.grand_line_auction_constants import KHY_CHANNEL_ID
from utils.db.auction_db import delete_auction, fetch_auction_by_channel_id
from utils.essentials.minimum_increment import (
    compute_maximum_auction_duration_seconds,
    compute_minimum_increment,
    format_names_for_market_value_lookup,
)
from utils.logs.debug_log import debug_log, enable_debug
from utils.logs.pretty_log import pretty_log
from utils.visuals.pretty_defer import pretty_defer


async def send_auction_house_banner(channel):
    """Sends the auction house banner to the specified channel."""
    content = Images.auction_house_open
    await channel.send(content)


async def stop_auction_func(
    bot: commands.Bot,
    interaction: discord.Interaction,
):
    """Stops an active auction in the current channel"""
    loader = await pretty_defer(
        interaction=interaction, content="Stopping auction...", ephemeral=False
    )

    channel_id = interaction.channel_id
    # Check if there's an active auction in this channel
    auction = await fetch_auction_by_channel_id(bot, channel_id)
    if not auction:
        await loader.error(content="No active auction found in this channel.")
        return
    is_bulk = auction.get("is_bulk", False)
    if not is_bulk:

        formatted_display = format_names_for_market_value_lookup(auction["pokemon"])
    else:
        formatted_display = "Bulk Pokemon"
    # Delete the auction from the database
    await delete_auction(bot, channel_id)
    pretty_log(
        tag="auction",
        message=f"Auction for {auction['pokemon']} ended by {interaction.user.display_name} in channel ID {channel_id}",
        bot=bot,
    )

    await loader.success(
        content=f"Auction for {formatted_display.title()} has stopped."
    )
