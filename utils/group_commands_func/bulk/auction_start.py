import re
import time
from collections import defaultdict

import discord
from discord.ext import commands

from constants.aesthetic import Images
from constants.rarity import RARITY_MAP, get_rarity, is_mon_auctionable
from utils.autocomplete.pokemon_autocomplete import format_price_w_coin
from utils.db.auction_db import upsert_auction
from utils.essentials.auction_broadcast import broadcast_auction
from utils.essentials.minimum_increment import (
    MIN_AUCTION_VALUE,
    compute_maximum_auction_duration_seconds,
    compute_minimum_increment_for_bulk,
    compute_total_bulk_value,
)
from utils.group_commands_func.auction.start import (
    check_and_load_auction_and_market_cache,
    make_auction_embed,
    TESTING,
    TESTING_DURATION,
    TEST_ENDS_ON,
    TESTING_BROADCAST
)
from utils.logs.debug_log import debug_log, enable_debug
from utils.logs.pretty_log import pretty_log
from utils.parser.duration_parser import parse_duration
from utils.parser.number_parser import parse_compact_number
from utils.visuals.pretty_defer import pretty_defer

# enable_debug(f"{__name__}.bulk_start_auction_func")



MAX_DURATION_SECONDS = 18_000


def extract_pokemon_list_and_validate(pokemon):
    """
    Extracts a list of Pokémon from a comma-separated string.
    Accepts entries like '2 shiny cottonee' and combines duplicates.
    Invalidates entries like 'shiny cottonee 2'.
    Returns: valid_pokemon (list of (name, qty)), invalid_pokemon (list), rarities (list), total_count (int)
    """
    valid_pokemon = []
    invalid_pokemon = []
    rarities = []
    count_map = defaultdict(int)
    total_count = 0

    if not pokemon:
        return [], [], [], 0

    for p in pokemon.split(","):
        p = p.strip().lower()
        if not p:
            continue
        # Match "quantity pokemon" (quantity can be compact number)
        match = re.match(r"^([\d,.a-z]+)\s+(.+)$", p)
        if match:
            qty_raw = match.group(1).replace(",", "")
            name = match.group(2).strip()
            qty = parse_compact_number(qty_raw)
            # Reject if name ends with a number (e.g., "shiny cottonee 2") or qty is invalid
            if re.search(r"\d+$", name) or qty is None:
                invalid_pokemon.append(p)
                continue
        else:
            # Reject if number at end
            if re.search(r"\d+$", p):
                invalid_pokemon.append(p)
                continue
            qty = 1
            name = p

        if is_mon_auctionable(name):
            rarity = get_rarity(name)
            rarities.append(rarity)
            count_map[name] += qty
            total_count += qty
        else:
            invalid_pokemon.append(p)

    valid_pokemon = [(name, count) for name, count in count_map.items()]
    return valid_pokemon, invalid_pokemon, rarities, total_count


async def bulk_start_auction_func(
    bot: commands.Bot,
    interaction: discord.Interaction,
    pokemon: str,
    duration: str,
    autobuy: str = None,
    accepted_pokemon: str = None,
):
    channel_name = (
        interaction.channel.name if interaction.channel else "Unknown Channel"
    )
    loader = await pretty_defer(
        interaction=interaction, content="Generating embed...", ephemeral=False
    )

    from utils.cache.auction_cache import (
        if_user_has_ongoing_auction_cache,
        is_there_ongoing_auction_cache,
    )

    # Check if caches are populated
    auc, market = await check_and_load_auction_and_market_cache(bot)
    if not auc or not market:
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

        valid_pokemon, invalid_pokemon, rarities, total_pokemon = (
            extract_pokemon_list_and_validate(pokemon)
        )
        if invalid_pokemon:
            debug_log(f"Invalid Pokémon in the list: {invalid_pokemon}")
            content = (
                f"We couldn't find the following pokemon in our list: {', '.join(invalid_pokemon)}\n"
                f"Kindly check the spelling, prefix, or check if the pokemon is in game. Contact auctioneer if you think this is a mistake.\n"
            )
            await loader.error(content=content)
            return
        # Return if more than 1 rarity is found in the bulk, as this should not happen since we are only accepting pokemon of the same rarity for bulks, but just in case
        if len(set(rarities)) > 1:
            debug_log(f"Multiple rarities found in the bulk: {rarities}")
            content = f"We found multiple rarities in the bulk: {', '.join(set(rarities))}. Please ensure all Pokémon in the bulk are of the same rarity."
            await loader.error(content=content)
            return
        rarity = rarities[0] if rarities else "Unknown"

        if total_pokemon == 1:
            debug_log(
                f"Only one Pokémon found in the bulk. Redirecting to single auction flow."
            )
            content = f"We found only one Pokémon in the bulk: {valid_pokemon[0][0]} (quantity: {valid_pokemon[0][1]}). Bulk Auctions need more than 1 Pokemon to auction."
            await loader.error(content=content)
            return

        # Compute total bulk value and check if it's auctionable
        total_bulk_value, has_market_value, has_no_market_value, any_exclusive = (
            compute_total_bulk_value(valid_pokemon)
        )
        if has_no_market_value:
            debug_log(
                f"Some Pokémon in the bulk do not have market values: {has_no_market_value}"
            )
            content = (
                f"The following Pokémon do not have market values and cannot be auctioned: {', '.join([f'{name} (quantity: {quantity})' for name, quantity, _ in has_no_market_value])}\n"
                f"Kindly check the spelling or check if the pokemon is in game. Contact auctioneer if you think this is a mistake.\n"
            )
            await loader.error(content=content)
            return
        if total_bulk_value < MIN_AUCTION_VALUE:
            debug_log(
                f"Total bulk value {total_bulk_value} is below the minimum auction value {MIN_AUCTION_VALUE}."
            )
            content = (
                f"The total market value of the bulk is {format_price_w_coin(total_bulk_value)}, which is below the minimum required to start an auction ({format_price_w_coin(MIN_AUCTION_VALUE)}).\n"
                f"Please include higher value Pokémon in the bulk to meet the minimum requirement.\n"
            )
            await loader.error(content=content)
            return

        # Compute minimum increment to validate auctionability and get duration limit
        min_increment, msg = compute_minimum_increment_for_bulk(
            total_bulk_value, rarity, any_exclusive
        )
        if min_increment == 0:
            debug_log(f"Could not compute minimum increment for {pokemon}.")
            await loader.error(content=msg)
            return
        if msg:
            debug_log(f"Minimum increment message for {pokemon}: {msg}")
            await loader.error(content=msg)
            return
        debug_log(f"Minimum increment for {pokemon} is {min_increment}.")

        # Compute maximum duration for the bulk based on its total value
        max_duration_seconds = compute_maximum_auction_duration_seconds(
            total_bulk_value
        )
        debug_log(
            f"Maximum auction duration for {pokemon} is {max_duration_seconds} seconds."
        )

        try:
            normalized_duration, unix_end = parse_duration(
                duration, max_duration_seconds
            )
            debug_log(
                f"Parsed duration: normalized={normalized_duration}, unix_end={unix_end}"
            )
            if unix_end - int(time.time()) > MAX_DURATION_SECONDS:
                debug_log(f"Duration too long: {unix_end - int(time.time())} seconds")
                await loader.error(content=f"Duration too long. Maximum is 5 hours.")
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

        gif_url = Images.bulk_auction
        if TESTING_DURATION:
            unix_end = TEST_ENDS_ON
        try:
            auction_embed, content = make_auction_embed(
                bot=bot,
                user=user,
                pokemon=pokemon,
                unix_end=str(unix_end),
                autobuy=real_autobuy,
                accepted_pokemon=accepted_pokemon,
                min_increment=min_increment,
                gif_url=gif_url,
                is_bulk=True,
                bulk_rarity=rarity,
            )
            await loader.success(content="", embed=auction_embed, add_check_emoji=False)
            auction_msg = await interaction.channel.send(content=content)
        except Exception as e:
            debug_log(f"Error generating or sending auction embed: {e}")
            pretty_log("error", f"Error generating or sending auction embed: {e}")
            await loader.error(
                content="An error occurred while generating or sending the auction embed."
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
                market_value=total_bulk_value,
                minimum_increment=min_increment,
                is_bulk=True,
            )
            pretty_log(
                "auction",
                f"Started bulk auction for {pokemon} with total value {total_bulk_value} and minimum increment {min_increment} in channel {channel_name}",
            )
        except Exception as e:
            debug_log(f"Error upserting auction: {e}")
            pretty_log("error", f"Error upserting auction: {e}", include_trace=True)
            await loader.error(
                content="An error occurred while saving the auction data."
            )
            return

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
