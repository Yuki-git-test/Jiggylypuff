import time
from datetime import datetime

import discord
from discord.ext import commands

from constants.auction import AUCTION_CATEGORY_LIST, MIN_AUCTION_VALUE
from constants.grand_line_auction_constants import (
    GLA_SERVER_ID,
    GRAND_LINE_AUCTION_CATEGORIES,
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
    auction_cache,
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
from utils.logs.debug_log import debug_log, enable_debug
from utils.logs.pretty_log import pretty_log
from utils.parser.duration_parser import format_seconds, parse_duration
from utils.parser.number_parser import parse_compact_number
from utils.visuals.get_pokemon_gif import get_pokemon_gif
from utils.visuals.pretty_defer import pretty_defer

TESTING_CATEGORIES = True
CATEGORY_ORDER = {
    0: GRAND_LINE_AUCTION_CATEGORIES.BULK_AUCTION,
    1: GRAND_LINE_AUCTION_CATEGORIES.GOLDEN_AUCTION,
    2: GRAND_LINE_AUCTION_CATEGORIES.SHINY_AUCTION,
    3: GRAND_LINE_AUCTION_CATEGORIES.GIGANTAMAX_AUCTION,
    4: GRAND_LINE_AUCTION_CATEGORIES.MEGA_AUCTION,
    5: GRAND_LINE_AUCTION_CATEGORIES.LEGENDARY_AUCTION,
    6: GRAND_LINE_AUCTION_CATEGORIES.EXCLUSIVE_AUCTIONS,
}


def is_auction_channel(channel: discord.TextChannel, user: discord.Member) -> bool:
    server_booster_role = channel.guild.get_role(
        GRAND_LINE_AUCTION_ROLES.server_booster
    )
    if channel.id == GRAND_LINE_AUCTION_TEXT_CHANNELS.test_auction:
        return True, None
    if channel.id == GRAND_LINE_AUCTION_TEXT_CHANNELS.booster_auction:
        if server_booster_role and server_booster_role in user.roles:
            return True, None
        else:
            return (
                False,
                "This channel is reserved for server boosters. Please use the appropriate auction channel for your auction.",
            )
    if (
        channel.category.id in AUCTION_CATEGORY_LIST
        or channel.category.id == GRAND_LINE_AUCTION_CATEGORIES.STAFF
        or channel.category.id == GRAND_LINE_AUCTION_CATEGORIES.PRIV_CHANNELS
    ):
        return True, None
    return (
        False,
        "This command can only be used in auction channels. Please use the appropriate channel for your auction.",
    )


def check_if_right_channel_rarity(
    channel: discord.TextChannel,
    rarity: str,
    is_exclusive: bool,
    is_bulk: bool = False,
    is_speed: bool = False,
) -> tuple[bool, str | None]:
    if is_speed:
        return True, None

    if not TESTING_CATEGORIES and (
        channel.id == GRAND_LINE_AUCTION_TEXT_CHANNELS.test_auction
        or channel.category.id == GRAND_LINE_AUCTION_CATEGORIES.STAFF
        or channel.category.id == GRAND_LINE_AUCTION_CATEGORIES.PRIV_CHANNELS
    ):
        return True, None

    category_id = channel.category.id
    category_rarity_list = RARITY_MAP.get(rarity, {}).get("category", []).copy()
    if is_exclusive:
        exclusive_category = RARITY_MAP.get("exclusive", {}).get("category", [])
        category_rarity_list.extend(exclusive_category)
    if is_bulk:
        bulk_category = RARITY_MAP.get("bulk", {}).get("category", [])
        category_rarity_list.extend(bulk_category)
    if category_id in category_rarity_list:
        return True, None

    valid_category_names = []
    for cat_id in category_rarity_list:
        cat_obj = discord.utils.get(channel.guild.categories, id=cat_id)
        if cat_obj:
            valid_category_names.append(cat_obj.name.title())
        else:
            valid_category_names.append(str(cat_id).title())
    # Ensure 'Bulk Auction' is always first if present
    bulk_name = "Bulk Auction"
    sorted_names = valid_category_names.copy()
    if bulk_name in sorted_names:
        sorted_names.remove(bulk_name)
        sorted_names = [bulk_name] + sorted_names
    bullet_lines = [f"> - {name}" for name in sorted_names]
    valid_names_str = "\n".join(bullet_lines)
    suggested_category = (
        "❤️‍🩹 You can't auction this Pokémon in this channel. Please use one of the following categories for this Pokémon:\n"
        + valid_names_str
        + "\n."
    )
    return False, suggested_category
