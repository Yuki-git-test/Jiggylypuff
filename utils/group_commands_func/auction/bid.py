import time

import discord
from discord.ext import commands

from utils.autocomplete.pokemon_autocomplete import format_price_w_coin
from utils.cache.auction_cache import get_auction_cache
from utils.cache.cache_list import ongoing_bidding
from utils.db.auction_db import delete_auction, update_auction_bid
from utils.functions.webhook_func import send_auction_log
from utils.group_commands_func.auction.stop import send_auction_house_banner
from utils.logs.debug_log import debug_log, enable_debug
from utils.logs.pretty_log import pretty_log
from utils.parser.number_parser import parse_compact_number
from utils.visuals.pretty_defer import pretty_defer

from .start import is_being_processed, make_auction_embed

INITIAL_MIN_BID = 100_000

TESTING = True  # Set to False when not testing


async def bid_func(
    bot: commands.Bot,
    interaction: discord.Interaction,
    amount: str,
):
    """Handles the logic for placing a bid in an auction."""
    guild = interaction.guild
    loader = await pretty_defer(
        interaction=interaction, content="Placing your bid...", ephemeral=True
    )

    # Get auction details from cache
    auction = get_auction_cache(interaction.channel_id)
    if not auction:
        await loader.error(content="This channel does not have an active auction.")
        return
    ends_on = auction["ends_on"]
    current_time = int(time.time())

    # Don't allow bidding if auction has ended
    if current_time >= ends_on and not TESTING:
        await loader.error(content="This auction has already ended.")
        return

    host_id = auction["host_id"]
    highest_bidder_id = auction["highest_bidder_id"]
    if interaction.user.id == host_id and not TESTING:
        await loader.error(content="You cannot bid on your own auction.")
        return

    if highest_bidder_id and interaction.user.id == highest_bidder_id and not TESTING:
        await loader.error(content="You are already the highest bidder.")
        return

    # Check if auction is being processed
    processing_message = is_being_processed(interaction.channel.id)
    if processing_message:
        await loader.error(content=processing_message)
        return
    # Mark this auction as being processed
    ongoing_bidding.add(interaction.channel.id)

    # Validate bid amount
    amount_value = parse_compact_number(amount)
    if not amount_value or amount_value <= 0:
        ongoing_bidding.remove(interaction.channel_id)
        await loader.error(content="Please enter a valid bid amount.")
        return

    # Get values
    autobuy = auction["autobuy"]
    highest_offer = auction["highest_offer"]
    highest_bidder_id = auction["highest_bidder_id"]
    minimum_increment = auction["minimum_increment"]
    is_bulk = auction.get("is_bulk", False)
    host_id = auction["host_id"]
    host = guild.get_member(host_id)
    is_initial_bid = False
    is_autobought = False
    last_bidder_mention = None
    total_minimum = highest_offer + minimum_increment
    context = "initial_bid"
    debug_log(f"Bid check: amount_value={amount_value}, total_minimum={total_minimum}")
    # Invalid bids lower than the current highest offer
    if amount_value < highest_offer:
        ongoing_bidding.remove(interaction.channel.id)
        await loader.error(
            content=f"Your bid must be higher than the current highest offer of {format_price_w_coin(highest_offer)}."
        )
        return

    # Check if bid meets or exceeds autobuy price
    if autobuy > 0 and amount_value >= autobuy:
        amount_value = autobuy  # Cap the bid at the autobuy price
        is_autobought = True

    # Check if initial bid
    elif highest_offer == 0:
        is_initial_bid = True
        if amount_value < INITIAL_MIN_BID:
            ongoing_bidding.remove(interaction.channel_id)
            await loader.error(
                content=f"The initial bid must be at least {format_price_w_coin(INITIAL_MIN_BID)}."
            )
            return

    # Check if bid is less than current highest offer + minimum increment

    elif amount_value < total_minimum:
        ongoing_bidding.remove(interaction.channel_id)
        await loader.error(
            content=f"Your bid must be at least {format_price_w_coin(total_minimum)} (current highest offer + minimum increment)."
        )
        return

    if not is_initial_bid:
        last_bidder_mention = f"<@{highest_bidder_id}>"
        context = "outbid"
    if is_autobought:
        # Update auction in database
        context = "autobought"

    # Create embed for bid confirmation
    try:
        new_embed, content = make_auction_embed(
            bot=bot,
            user=host,
            pokemon=auction["pokemon"],
            unix_end=str(auction["ends_on"]),
            accepted_pokemon=auction["accepted_list"],
            gif_url=auction["image_link"],
            context=context,
            min_increment=minimum_increment,
            highest_offer=amount_value,
            highest_bidder=interaction.user,
            last_bidder_mention=last_bidder_mention,
            autobuy=autobuy,
            is_bulk=is_bulk,
        )
    except Exception as e:
        ongoing_bidding.remove(interaction.channel_id)
        pretty_log("error", f"Error creating auction embed: {e}", include_trace=True)
        await loader.error(content="An error occurred while placing your bid.")
        return

    try:
        await update_auction_bid(
            bot=bot,
            channel_id=interaction.channel_id,
            highest_bidder_id=interaction.user.id,
            highest_bidder=interaction.user.name,
            highest_offer=amount_value,
        )

    except Exception as e:
        ongoing_bidding.remove(interaction.channel_id)
        pretty_log("error", f"Error updating auction bid: {e}", include_trace=True)
        await loader.error(content="An error occurred while placing your bid.")
        return

    # Send updated embed
    await interaction.channel.send(embed=new_embed)
    if content:
        await interaction.channel.send(content=content)
    await loader.success(content="Your bid has been placed successfully!")
    if is_autobought:
        # Remove from db
        await delete_auction(bot, channel_id=interaction.channel_id)
        await send_auction_house_banner(interaction.channel)
        ongoing_bidding.remove(interaction.channel_id)
        await send_auction_log(
            bot=bot,
            embed=new_embed,
        )

    ongoing_bidding.remove(interaction.channel_id)
    pretty_log(
        "auction",
        f"User {interaction.user} placed a bid of {format_price_w_coin(amount_value)} in channel {interaction.channel.name} Autobought: {is_autobought}",
    )
