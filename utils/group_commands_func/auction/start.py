import time
from datetime import datetime

import discord
from discord.ext import commands

from constants.auction import MIN_AUCTION_VALUE
from constants.grand_line_auction_constants import (
    GLA_SERVER_ID,
    GRAND_LINE_AUCTION_ROLES,
    GRAND_LINE_AUCTION_TEXT_CHANNELS,
    KHY_CHANNEL_ID,
)
from constants.rarity import (
    RARITY_MAP,
    get_rarity,
    is_mon_auctionable,
    is_mon_exclusive,
)
from utils.autocomplete.pokemon_autocomplete import format_price_w_coin
from utils.cache.auction_cache import check_cache_and_reload_if_missing
from utils.cache.cache_list import (
    ongoing_bidding,
    processing_auction_end,
    processing_roll_back,
    processing_update_ends_on,
)
from utils.db.auction_db import upsert_auction
from utils.db.market_value_db import (
    check_and_load_market_cache,
    fetch_lowest_market_value_cache,
)
from utils.essentials.auction_broadcast import broadcast_auction
from utils.essentials.minimum_increment import (
    compute_maximum_auction_duration_seconds,
    compute_minimum_increment,
    format_names_for_market_value_lookup,
)
from utils.functions.auction import check_if_right_channel_rarity, is_auction_channel
from utils.logs.debug_log import debug_log, enable_debug
from utils.logs.pretty_log import pretty_log
from utils.parser.duration_parser import format_seconds, parse_duration
from utils.parser.number_parser import parse_compact_number
from utils.visuals.get_pokemon_gif import get_pokemon_gif
from utils.visuals.pretty_defer import pretty_defer

#enable_debug(f"{__name__}.start_auction_func")

# Max duration is 300 minutes (5 hours)
TESTING = True


TESTING_DURATION = False
# Test ends on is set to 3 minutes from now to allow testing of end time related features. Remember to set TESTING_DURATION to False when done testing.
TEST_ENDS_ON = int(time.time()) + 180


MAX_DURATION_SECONDS = 18_000
TESTING_BROADCAST = False
TESTING_SPEED_AUCTION = False


def is_speed_auction(channel: discord.TextChannel) -> bool:
    """Returns True if the auction in the given channel is a speed auction, otherwise False."""
    if TESTING_SPEED_AUCTION:
        return True

    if channel.id == GRAND_LINE_AUCTION_TEXT_CHANNELS.speed_auction:
        return True
    else:
        return False


async def check_and_load_auction_and_market_cache(bot: commands.Bot):
    """Checks and loads auction and market value caches."""
    auc_cache = await check_cache_and_reload_if_missing(bot)
    market_cache = await check_and_load_market_cache(bot)
    return auc_cache, market_cache


def is_being_processed(channel_id: int) -> str | None:
    """Returns a custom error message if the auction in the given channel is being processed, otherwise None."""
    if channel_id in ongoing_bidding:
        return "Another bid is currently being processed. Please wait a moment and try again."
    if channel_id in processing_auction_end:
        return "This auction is currently being ended. You cannot place a bid at this time."
    if channel_id in processing_roll_back:
        return "A bid rollback is currently being processed for this auction. Please wait a moment and try again."
    if channel_id in processing_update_ends_on:
        return "An update to the auction end time is already being processed for this channel. Please wait."
    return None


def make_auction_embed(
    bot,
    user: discord.User | discord.Member,
    pokemon: str,
    unix_end: str,
    autobuy: str = None,
    accepted_pokemon: str = None,
    gif_url: str = None,
    context: str = "auction",
    message_link: str = None,
    highest_offer: str = None,
    highest_bidder: discord.Member | discord.User = None,
    last_bidder_mention: str = None,
    is_bulk: bool = False,
    min_increment: int = None,
    bulk_rarity: str = None,
):
    guild = bot.get_guild(GLA_SERVER_ID)

    if not is_bulk:
        pokemon = format_names_for_market_value_lookup(pokemon).title()
        rarity = get_rarity(pokemon)
    else:
        pokemon = "Bulk"
        rarity = bulk_rarity

    rarity_details = RARITY_MAP.get(rarity, {})
    debug_log(f"Rarity details: {rarity_details}")
    color = rarity_details.get("color", 0xFFFFFF)
    emoji = rarity_details.get("emoji", "")
    auction_roles_ids = rarity_details.get("auction role", [])
    debug_log(f"Auction role IDs: {auction_roles_ids}")
    bulk_auction_role = guild.get_role(GRAND_LINE_AUCTION_ROLES.bulk_auction)
    auction_roles_objs = [guild.get_role(role_id) for role_id in auction_roles_ids]

    if is_bulk:
        # Insert bulk_auction_role at the start
        auction_roles_objs = [bulk_auction_role] + auction_roles_objs

    debug_log(f"Auction role objects: {auction_roles_objs}")
    exclusive_auction_role = guild.get_role(GRAND_LINE_AUCTION_ROLES.exclusive_auction)
    auction_roles_str = (
        ", ".join(role.name for role in auction_roles_objs if role)
        if auction_roles_objs
        else exclusive_auction_role.name if exclusive_auction_role else "None"
    )
    content = ""
    duration_str = f"<t:{unix_end}:R>"
    accepted_pokemon_str = "✅" if accepted_pokemon else "❌"
    pokemon_name = pokemon.title()
    display_name = f"{emoji} {pokemon_name}" if emoji else pokemon_name
    coin_autobuy = format_price_w_coin(autobuy) if autobuy is not None else "N/A"
    debug_log(
        f"Embed values: color={color}, emoji={emoji}, coin_autobuy={coin_autobuy}"
    )
    embed = discord.Embed(
        color=color,
        timestamp=datetime.now(),
    )
    embed.set_author(name=f"{user.name}'s Auction", icon_url=user.avatar.url)
    if message_link:
        embed.add_field(
            name="Auction Link",
            value=f"[Jump to Auction]({message_link})",
            inline=False,
        )
    embed.add_field(name="Pokémon", value=display_name, inline=False)
    duration_str = f"<t:{unix_end}:R>"
    if context == "ended" or context == "autobought":
        duration_str = "Auction Ended"
    embed.add_field(name="Auction Ends", value=duration_str, inline=False)
    # Autobuy field: show N/A if not provided or zero
    if autobuy is None or autobuy == 0:
        debug_log("Autobuy is None or 0, setting to N/A")
        embed.add_field(name="Autobuy Price", value="N/A", inline=True)
    else:
        embed.add_field(name="Autobuy Price", value=coin_autobuy, inline=True)
    embed.add_field(name="Accepted Pokémon", value=accepted_pokemon_str, inline=True)

    # Highest Offer/Bidder: only one set of fields
    show_na_offer = (context in ("auction", "broadcast")) and (
        not highest_offer or highest_offer == 0
    )
    if show_na_offer:
        debug_log("No highest offer, showing N/A for offer and bidder")
        embed.add_field(name="Highest Offer", value="N/A", inline=False)
        embed.add_field(name="Highest Bidder", value="N/A", inline=True)
    elif context == "autobought":
        value_str = (
            getattr(highest_bidder, "mention", "N/A") if highest_bidder else "N/A"
        )
        debug_log(f"Showing Autobought, bidder: {value_str}")
        embed.add_field(name="Highest Offer", value="Autobought", inline=False)
        embed.add_field(name="Highest Bidder", value=value_str, inline=True)
    else:
        formatted_highest_offer = (
            format_price_w_coin(highest_offer) if highest_offer else "N/A"
        )
        value_str = (
            getattr(highest_bidder, "mention", "N/A") if highest_bidder else "N/A"
        )
        debug_log(
            f"Showing highest offer: {formatted_highest_offer}, bidder: {value_str}"
        )
        embed.add_field(
            name="Highest Offer", value=formatted_highest_offer, inline=False
        )
        embed.add_field(name="Highest Bidder", value=value_str, inline=True)

    # Deciding content based on context
    debug_log(f"Deciding content for context: {context}")
    if context == "auction":
        content = f"{auction_roles_str} {pokemon_name} is up for auction!"
    elif context == "broadcast":
        content = ""
    elif context == "ended" and not highest_bidder:
        content = f"{user.mention}, your auction has ended with no bids placed."
    elif (context == "ended" or context == "autobought") and highest_bidder:
        content = f"Auction ended!!! {highest_bidder.mention} pls ping {user.mention} in <#1342073980688928829> to <#1342074030894743602> to claim"
    elif context == "outbid":
        content = f"{highest_bidder.mention} has outbidded you {last_bidder_mention}"
    elif (
        context == "initial_bid"
        or context == "roll_back"
        or context == "update_ends_on"
        or context == "update_bid"
    ):
        content = ""
    if context != "broadcast":
        embed.set_footer(
            text=f"Minimum Increment: {min_increment:,}",
            icon_url=guild.icon.url if guild.icon else None,
        )
    embed.set_image(url=gif_url)
    debug_log(f"Embed fields: {[f.name for f in embed.fields]}")
    return embed, content


async def send_to_khy_channel(
    guild: discord.Guild,
    content: str = None,
    embed: discord.Embed = None,
):
    khy_channel = guild.get_channel(KHY_CHANNEL_ID)
    if khy_channel:
        await khy_channel.send(content=content, embed=embed)


async def start_auction_func(
    bot: commands.Bot,
    interaction: discord.Interaction,
    pokemon: str,
    duration: str,
    autobuy: str = None,
    accepted_pokemon: str = None,
):
    loader = await pretty_defer(
        interaction=interaction, content="Generating embed...", ephemeral=False
    )

    from utils.cache.auction_cache import (
        if_user_has_ongoing_auction_cache,
        is_there_ongoing_auction_cache,
    )

    # Check if caches are populated
    auc, market = await check_and_load_auction_and_market_cache(bot)
    if auc is None or market is None:
        await loader.error(
            content="Caches are still loading. Please try again in a moment."
        )
        return

    if is_there_ongoing_auction_cache(interaction.channel.id):
        await loader.error(
            content="There is already an ongoing auction in this channel."
        )
        return

    try:
        user = interaction.user
        debug_log(
            f"Received test_embed command with pokemon={pokemon}, duration={duration}, autobuy={autobuy}, accepted_pokemon={accepted_pokemon}"
        )
        # Check if user has an ongoing auction
        status, max_auctions_allowed, ongoing_auctions_count = (
            if_user_has_ongoing_auction_cache(user)
        )
        if status:
            await loader.error(
                content=f"You already have {ongoing_auctions_count} ongoing auction(s). The maximum allowed is {max_auctions_allowed}."
            )
            return
        # Check if auction channel
        passed, error_msg = is_auction_channel(interaction.channel, user)
        if not passed:
            await loader.error(content=error_msg)
            return

        # Check if right category for rarity
        if not is_mon_auctionable(pokemon):
            debug_log(f"{pokemon} is not auctionable.")
            await loader.error(
                content=f"{pokemon} is not an auctionable Pokémon. Please choose a different one."
            )
            return
        is_speed_auc = is_speed_auction(interaction.channel)
        rarity = get_rarity(pokemon)
        debug_log(f"Rarity: {rarity}")
        if not rarity:
            debug_log(f"Missing rarity for {pokemon}")
            await loader.error(content=f"Could not determine the rarity of {pokemon}.")
            content = f"Missing Rarity for {pokemon}"
            await send_to_khy_channel(interaction.guild, content=content)
            return

        # Compute minimum increment to validate auctionability and get duration limit
        min_increment, msg = compute_minimum_increment(pokemon, rarity)
        if min_increment == 0:
            debug_log(f"Could not compute minimum increment for {pokemon}.")
            await loader.error(content=msg)
            return
        if msg:
            debug_log(f"Minimum increment message for {pokemon}: {msg}")
            await loader.error(content=msg)
            return
        debug_log(f"Minimum increment for {pokemon} is {min_increment}.")

        # Ensure consistent formatting for market value lookup
        from utils.essentials.minimum_increment import (
            format_names_for_market_value_lookup,
        )

        formatted_pokemon = format_names_for_market_value_lookup(pokemon)
        lowest_market_value = fetch_lowest_market_value_cache(formatted_pokemon)
        debug_log(
            f"Lowest market value for {formatted_pokemon} is {lowest_market_value}."
        )
        max_duration_seconds = compute_maximum_auction_duration_seconds(
            lowest_market_value
        )
        debug_log(
            f"Maximum auction duration for {pokemon} is {max_duration_seconds} seconds."
        )

        try:
            normalized_duration, unix_end, max_parse_seconds = parse_duration(
                duration, max_duration_seconds, is_speed_auc=is_speed_auc
            )
            debug_log(
                f"Parsed duration: normalized={normalized_duration}, unix_end={unix_end}"
            )
            if unix_end - int(time.time()) > max_parse_seconds:
                debug_log(f"Duration too long: {unix_end - int(time.time())} seconds")
                await loader.error(
                    content=f"Duration too long. Maximum is {format_seconds(max_parse_seconds)}."
                )
                return
        except ValueError as e:
            debug_log(f"Duration parse error: {e}")
            await loader.error(content=str(e))
            return

        real_autobuy = None
        display_autobuy = "N/A"
        if autobuy:
            real_autobuy = parse_compact_number(autobuy)
            debug_log(f"Parsed autobuy: {real_autobuy}")
            display_autobuy = f"{real_autobuy:,}" if real_autobuy is not None else "N/A"
            if real_autobuy is None:
                debug_log("Invalid autobuy amount provided.")
                await loader.error(
                    content="Invalid autobuy amount. Please provide a number like `1k`, `1.5m`, etc."
                )
                return
            if real_autobuy < MIN_AUCTION_VALUE:
                format_min_value = format_price_w_coin(MIN_AUCTION_VALUE)
                debug_log(
                    f"Autobuy amount {real_autobuy} is below minimum initial value bid of {MIN_AUCTION_VALUE}."
                )
                await loader.error(
                    content=f"Autobuy amount must be at least {format_min_value}"
                )
                return

        gif_url = get_pokemon_gif(pokemon)
        debug_log(f"GIF URL: {gif_url}")
        if not gif_url:
            debug_log(f"Missing GIF for {pokemon}")
            await loader.error(content=f"Could not find a GIF for that {pokemon}.")
            content = f"Missing Gif for {pokemon}"
            await send_to_khy_channel(interaction.guild, content=content)
            return
        if TESTING_DURATION:
            unix_end = TEST_ENDS_ON
        rarity = get_rarity(pokemon)
        debug_log(f"Rarity: {rarity}")
        is_exclusive = is_mon_exclusive(pokemon)
        success, msg = check_if_right_channel_rarity(
            interaction.channel,
            rarity,
            is_exclusive=is_exclusive,
            is_bulk=False,
            is_speed=is_speed_auc,
        )
        if msg:
            debug_log(f"Channel rarity check failed: {msg}")
            await loader.error(content=msg)
            return
        try:
            auction_embed, content = make_auction_embed(
                bot=bot,
                user=user,
                pokemon=pokemon,
                unix_end=str(unix_end),
                autobuy=real_autobuy,
                accepted_pokemon=accepted_pokemon,
                gif_url=gif_url,
                min_increment=min_increment,
            )
        except Exception as e:
            debug_log(f"Error creating auction embed: {e}")
            pretty_log("error", f"Error in test_embed command: {e}")
            await loader.error(
                content="An unexpected error occurred while generating the embed."
            )
            return
        try:
            await upsert_auction(
                bot=bot,
                channel_id=interaction.channel.id,
                channel_name=interaction.channel.name,
                host_id=user.id,
                host_name=user.name,
                pokemon=pokemon,
                highest_bidder_id=0,
                highest_bidder="",
                highest_offer=0,
                autobuy=real_autobuy if real_autobuy is not None else 0,
                ends_on=unix_end,
                accepted_list=accepted_pokemon if accepted_pokemon else "",
                image_link=gif_url,
                broadcast_msg_id=0,  # will update after broadcasting
                market_value=(
                    lowest_market_value if lowest_market_value is not None else 0
                ),
                minimum_increment=min_increment,
            )
        except Exception as e:
            debug_log(f"Error upserting auction: {e}")
            pretty_log("error", f"Error upserting auction: {e}", include_trace=True)
            await loader.error(
                content="An error occurred while saving the auction data."
            )
            return

        await loader.success(content="", embed=auction_embed, add_check_emoji=False)
        if is_speed_auc:
            speed_auc_role = interaction.guild.get_role(
                GRAND_LINE_AUCTION_ROLES.speed_auction
            )
            if speed_auc_role:
                content = f"{speed_auc_role.name} " + content

        auction_msg = await interaction.channel.send(content=content)
        pretty_log(
            "auction",
            message=(
                f"Auction started for {pokemon} by {user.name} in channel {interaction.channel.name}. Duration: {duration}, Autobuy: {display_autobuy}, Accepted Pokémon: {accepted_pokemon if accepted_pokemon else 'None'}"
                f". Market Value: {lowest_market_value if lowest_market_value is not None else 'N/A'}. Minimum Increment: {min_increment:,}"
            ),
        )

        # Make broadcast embed, same with auction embed but no highest offer/bidder and with a footer about checking the auction channel
        broadcast_embed, broadcast_content = make_auction_embed(
            bot=bot,
            user=user,
            pokemon=pokemon,
            unix_end=str(unix_end),
            autobuy=real_autobuy,
            accepted_pokemon=accepted_pokemon,
            gif_url=gif_url,
            context="broadcast",
            message_link=auction_msg.jump_url,
        )

        if not TESTING or TESTING_BROADCAST:
            await broadcast_auction(
                bot=bot,
                guild=interaction.guild,
                embed=broadcast_embed,
            )

    except Exception as e:
        debug_log(f"Exception in test_embed: {e}")
        pretty_log("error", f"Error in test_embed command: {e}")
        await loader.error(
            content="An unexpected error occurred while generating the embed."
        )
