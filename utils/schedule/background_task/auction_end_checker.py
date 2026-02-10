import discord

from constants.grand_line_auction_constants import GLA_SERVER_ID
from utils.cache.cache_list import processing_auction_end
from utils.db.auction_db import delete_auction, fetch_all_due_auctions
from utils.group_commands_func.auction.end import send_auction_house_banner
from utils.group_commands_func.auction.start import make_auction_embed
from utils.logs.pretty_log import pretty_log
from utils.essentials.minimum_increment import (
    compute_maximum_auction_duration_seconds,
    compute_minimum_increment,
    format_names_for_market_value_lookup,
)

async def check_and_end_due_auctions(bot: discord.Client):
    due_auctions = await fetch_all_due_auctions(bot)
    if not due_auctions:
        return
    guild = bot.get_guild(GLA_SERVER_ID)
    if not guild:
        return
    for auction in due_auctions:
        channel_id = auction["channel_id"]
        processing_auction_end.add(channel_id)  # Add to processing set to prevent
        channel = guild.get_channel(channel_id)
        if not channel:
            # Remove auction from database if channel no longer exists
            await delete_auction(bot, channel_id)
            pretty_log(
                tag="auction",
                message=f"Deleted auction with channel ID {channel_id} because the channel no longer exists.",
                bot=bot,
            )
            processing_auction_end.remove(channel_id)
            continue
        # Get auction details
        host_id = auction["host_id"]
        is_bulk = auction.get("is_bulk", False)
        host = guild.get_member(host_id)
        if not host:
            # Fetch discord use
            host = await guild.fetch_member(host_id)
        highest_bidder_id = auction["highest_bidder_id"]
        highest_bidder = None
        if highest_bidder_id:
            highest_bidder = guild.get_member(highest_bidder_id)
            if not highest_bidder:
                highest_bidder = await guild.fetch_member(highest_bidder_id)
                if not highest_bidder:
                    highest_bidder = None

        # Remove auction from database
        try:
            await delete_auction(bot, channel_id)
        except Exception as e:
            pretty_log(
                tag="error",
                message=f"Error deleting auction with channel ID {channel_id}: {e}",
                include_trace=True,
                bot=bot,
            )
            processing_auction_end.remove(channel_id)
            continue
        # Send auction ended message
        try:
            embed, content = make_auction_embed(
                bot=bot,
                user=host,
                pokemon=auction["pokemon"],
                unix_end=auction["ends_on"],
                autobuy=auction["autobuy"],
                accepted_pokemon=auction["accepted_list"],
                gif_url=auction["image_link"],
                highest_offer=auction["highest_offer"] if highest_bidder else 0,
                highest_bidder=highest_bidder if highest_bidder else None,
                last_bidder_mention=auction.get("last_bidder_mention", None),
                context="ended",
                min_increment=auction["minimum_increment"],
                is_bulk=is_bulk,
            )
            await channel.send(embed=embed)
            await channel.send(content=content)
            processing_auction_end.remove(channel_id)
            await send_auction_house_banner(channel)
            pretty_log(
                tag="auction",
                message=f"Auction for {auction['pokemon']} ended in channel ID {channel_id}",
                bot=bot,
            )

        except Exception as e:
            pretty_log(
                tag="error",
                message=f"Error sending auction ended message for channel ID {channel_id}: {e}",
                include_trace=True,
                bot=bot,
            )
            processing_auction_end.remove(channel_id)
            continue
