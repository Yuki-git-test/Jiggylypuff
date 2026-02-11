import time
from datetime import datetime

import discord
from discord import app_commands
from discord.ext import commands

from constants.auction import MIN_INITIAL_BID
from constants.grand_line_auction_constants import (
    GRAND_LINE_AUCTION_ROLES,
    KHY_CHANNEL_ID,
)
from constants.rarity import RARITY_MAP, get_rarity, is_mon_auctionable
from utils.autocomplete.pokemon_autocomplete import (
    format_price_w_coin,
    pokemon_autocomplete,
)
from utils.cache.auction_cache import get_auction_cache
from utils.cache.cache_list import (
    ongoing_bidding,
    processing_auction_end,
    processing_roll_back,
)
from utils.db.auction_db import delete_auction, update_auction_bid, upsert_auction
from utils.db.market_value_db import fetch_lowest_market_value_cache
from utils.essentials.auction_broadcast import broadcast_auction
from utils.essentials.minimum_increment import (
    compute_maximum_auction_duration_seconds,
    compute_minimum_increment,
)
from utils.logs.debug_log import debug_log, enable_debug
from utils.logs.pretty_log import pretty_log
from utils.parser.duration_parser import parse_duration
from utils.parser.number_parser import parse_compact_number
from utils.visuals.get_pokemon_gif import get_pokemon_gif
from utils.visuals.pretty_defer import pretty_defer

from .start import is_being_processed, make_auction_embed


async def roll_back_func(
    bot: commands.Bot,
    interaction: discord.Interaction,
    member: discord.Member,
    amount: str,
):
    """Handles the logic for rolling back a bid in an auction. Only usable by auctioneers."""
    guild = interaction.guild
    channel_id = interaction.channel.id
    loader = await pretty_defer(
        interaction=interaction, content="Rolling back the bid...", ephemeral=False
    )
    channel_name = interaction.channel.name if interaction.channel else "Unknown Channel"
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

    host_id = auction["host_id"]
    highest_bidder_id = auction["highest_bidder_id"]
    if member.id == host_id:
        await loader.error(content="The host's bid cannot be rolled back.")
        return
    if member.id == highest_bidder_id:
        await loader.error(
            content=f"{member.display_name} is currently the highest bidder."
        )
        return

    if highest_bidder_id == 0:
        await loader.error(content="There are no bids to roll back.")
        return

    # Check if auction is being processed
    processing_message = is_being_processed(interaction.channel.id)
    if processing_message:
        await loader.error(content=processing_message)
        return
    # Mark this auction as being processed
    ongoing_bidding.add(interaction.channel.id)
    processing_roll_back.add(channel_id)

    try:
        amount_value = parse_compact_number(amount)
    except ValueError:
        processing_roll_back.remove(channel_id)
        await loader.error(
            content="Invalid amount format. Please enter a valid number (e.g. '1k', '1.5m')."
        )
        return
    if amount_value <= 0:
        processing_roll_back.remove(channel_id)
        await loader.error(content="Please enter a valid amount greater than 0.")
        return

    if amount_value < MIN_INITIAL_BID:
        processing_roll_back.remove(channel_id)
        await loader.error(
            content=f"The rolled back bid must be at least {format_price_w_coin(MIN_INITIAL_BID)}."
        )
        return
    # Get details
    pokemon = auction["pokemon"]
    host_id = auction["host_id"]
    host = guild.get_member(host_id)
    autobuy = auction["autobuy"]
    is_bulk = auction.get("is_bulk", False)

    # Create embed with new rolled back bid details
    try:
        embed, content = make_auction_embed(
            bot=bot,
            user=host,
            pokemon=pokemon,
            autobuy=autobuy,
            unix_end=str(auction["ends_on"]),
            accepted_pokemon=auction["accepted_list"],
            highest_offer=amount_value,
            min_increment=auction["minimum_increment"],
            highest_bidder=member,
            gif_url=auction["image_link"],
            context="roll_back",
            is_bulk=is_bulk,
        )
    except Exception as e:
        processing_roll_back.remove(channel_id)
        content = f"Error creating auction embed: {str(e)}"
        await loader.error(content=content)
        pretty_log(
            "error",
            f"Error creating auction embed during bid roll back in channel {channel_name}: {str(e)}",
        )
        return
    # Update auction in database
    try:
        await update_auction_bid(
            bot=bot,
            channel_id=channel_id,
            highest_bidder_id=member.id,
            highest_offer=amount_value,
        )
        await interaction.channel.send(embed=embed)
        await loader.success(content="Bid rolled back successfully.")
        processing_roll_back.remove(channel_id)
        pretty_log(
            "auction",
            f"Bid rolled back to {format_price_w_coin(amount_value)} for {member.display_name} by {interaction.user.name} in channel {channel_name}",
        )
    except Exception as e:
        processing_roll_back.remove(channel_id)
        content = f"Error updating auction bid in database: {str(e)}"
        await loader.error(content=content)
        pretty_log(
            "error",
            f"Error updating auction bid in database during bid roll back in channel {channel_name}: {str(e)}",
        )
        return
