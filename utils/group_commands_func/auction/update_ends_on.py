import time
from datetime import datetime

import discord
from discord.ext import commands

from utils.cache.auction_cache import get_auction_cache
from utils.cache.cache_list import processing_update_ends_on
from utils.db.auction_db import update_ends_on
from utils.logs.debug_log import debug_log, enable_debug
from utils.logs.pretty_log import pretty_log
from utils.parser.duration_parser import parse_total_seconds
from utils.visuals.pretty_defer import pretty_defer

from .start import is_being_processed, make_auction_embed


async def update_ends_on_func(
    bot: commands.Bot,
    interaction: discord.Interaction,
    action: str,
    duration: str,
):
    """Handles the logic for updating the ends_on time of an auction. Only usable by auctioneers."""
    channel_name = (
        interaction.channel.name if interaction.channel else "Unknown Channel"
    )
    guild = interaction.guild
    channel_id = interaction.channel.id
    loader = await pretty_defer(
        interaction=interaction, content="Updating ends on...", ephemeral=False
    )

    # Get auction details from cache
    auction = get_auction_cache(interaction.channel_id)
    if not auction:
        await loader.error(content="This channel does not have an active auction.")
        return

    # Don't allow bidding if auction has ended
    ends_on = auction["ends_on"]
    current_time = int(time.time())
    if current_time >= ends_on:
        await loader.error(content="This auction has already ended.")
        return

    try:
        total_seconds = parse_total_seconds(duration)
    except ValueError:
        await loader.error(
            content="Invalid duration format. Please enter a valid duration (e.g. '5m', '2h')."
        )
        return
    old_ends_on = auction["ends_on"]

    if action == "add":
        new_ends_on = old_ends_on + total_seconds
    elif action == "subtract":
        new_ends_on = old_ends_on - total_seconds
        # Check if  new ends on is in the past
        if new_ends_on < int(time.time()):
            await loader.error(content="You cannot set the end time to the past.")
            return

    processing_msg = is_being_processed(channel_id)
    if processing_msg:
        await loader.error(content=processing_msg)
        return
    processing_update_ends_on.add(channel_id)

    # Get details
    pokemon = auction["pokemon"]
    is_bulk = auction.get("is_bulk", False)
    host_id = auction["host_id"]
    host = guild.get_member(host_id)
    autobuy = auction["autobuy"]
    highest_offer = auction["highest_offer"]
    highest_bidder_id = auction["highest_bidder_id"]
    highest_bidder = None
    if highest_bidder_id:
        highest_bidder = guild.get_member(highest_bidder_id)
        if not highest_bidder:
            # Fetch user object
            highest_bidder = await bot.fetch_user(highest_bidder_id)
            if not highest_bidder:
                highest_bidder = None

    # Create embed with new rolled back bid details
    try:
        embed, content = make_auction_embed(
            bot=bot,
            user=host,
            pokemon=pokemon,
            autobuy=autobuy,
            unix_end=str(new_ends_on),
            accepted_pokemon=auction["accepted_list"],
            highest_offer=highest_offer,
            highest_bidder=highest_bidder,
            gif_url=auction["image_link"],
            context="update_ends_on",
            min_increment=auction["minimum_increment"],
            is_bulk=is_bulk,
        )
    except Exception as e:
        processing_update_ends_on.remove(channel_id)
        content = f"Error creating auction embed: {str(e)}"
        await loader.error(content=content)
        pretty_log(
            "error",
            f"Error creating auction embed during bid roll back in channel {channel_id}: {str(e)}",
        )
        return
    # Update auction in database
    try:
        await update_ends_on(bot=bot, channel_id=channel_id, ends_on=new_ends_on)
        await interaction.channel.send(embed=embed)
        await loader.success(content="Auction end time updated successfully.")
        processing_update_ends_on.remove(channel_id)
        pretty_log(
            "auction",
            f"Auction end time updated to {datetime.fromtimestamp(new_ends_on).strftime('%Y-%m-%d %H:%M:%S')} by {interaction.user.name} in channel {channel_name}",
        )
    except Exception as e:
        processing_update_ends_on.remove(channel_id)
        content = f"Error updating auction bid in database: {str(e)}"
        await loader.error(content=content)
        pretty_log(
            "error",
            f"Error updating auction bid in database during bid roll back in channel {channel_name}: {str(e)}",
        )
        return
