import discord

from constants.grand_line_auction_constants import (
    GLA_SERVER_ID,
    GRAND_LINE_AUCTION_ROLES,
    GRAND_LINE_AUCTION_TEXT_CHANNELS,
)
from utils.cache.cache_list import processing_auction_end
from utils.db.auction_db import (
    delete_auction,
    fetch_auctions_ending_within_10_mins,
    update_last_minute_pinged,
)
from utils.logs.pretty_log import pretty_log

TESTING = True


async def check_and_ping_last_minute_auctions(bot: discord.Client):
    """Checks for auctions that are ending within the next 10 minutes and sends a ping in the auction channel if not already pinged."""
    if TESTING:
        return

    auctions_ending_soon = await fetch_auctions_ending_within_10_mins(bot)
    if not auctions_ending_soon:
        return
    guild = bot.get_guild(GLA_SERVER_ID)
    if not guild:
        return
    for auction in auctions_ending_soon:
        channel_id = auction["channel_id"]
        if channel_id in processing_auction_end:
            continue  # Skip if auction is currently being processed for ending
        
        if channel_id == GRAND_LINE_AUCTION_TEXT_CHANNELS.speed_auction:
            # Update database to indicate ping has been sent without actually sending a message since speed auction channel is already very active and doesn't need ping
            await update_last_minute_pinged(bot, channel_id, True)
            continue

        channel = guild.get_channel(channel_id)
        if not channel:
            # Remove auction from database if channel no longer exists
            await delete_auction(bot, channel_id)
            pretty_log(
                tag="auction",
                message=f"Deleted auction with channel ID {channel_id} because the channel no longer exists.",
                bot=bot,
            )
            continue
        # Send last minute ping
        last_minute_ping_role = guild.get_role(GRAND_LINE_AUCTION_ROLES.last_min)
        # CHange to mention when done testing
        content = f"{last_minute_ping_role.name} Auction for {auction['pokemon']} is ending in less than 10 minutes!"
        try:
            await update_last_minute_pinged(
                bot, channel_id, True
            )  # Update database to indicate ping has been sent
            await channel.send(content=content)

            pretty_log(
                tag="auction",
                message=f"Sent last minute ping for auction in channel ID {channel_id}",
                bot=bot,
            )
        except Exception as e:
            pretty_log(
                tag="error",
                message=f"Error sending last minute ping for auction in channel ID {channel_id}: {e}",
                include_trace=True,
                bot=bot,
            )
            continue
