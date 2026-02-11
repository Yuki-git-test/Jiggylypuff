import discord

from constants.grand_line_auction_constants import GRAND_LINE_AUCTION_ROLES
from utils.cache.cache_list import auction_cache
from utils.db.auction_db import fetch_all_auctions
from utils.logs.pretty_log import pretty_log

# SQL SCRIPT
"""CREATE TABLE auctions (
    channel_id BIGINT PRIMARY KEY,
    channel_name VARCHAR(255),
    host_id BIGINT,
    host_name VARCHAR(255),
    pokemon VARCHAR(255),
    highest_bidder_id BIGINT,
    highest_bidder VARCHAR(255),
    highest_offer BIGINT,
    autobuy BIGINT,
    ends_on BIGINT,
    accepted_list TEXT,
    image_link TEXT,
    broadcast_msg_id BIGINT,
    market_value BIGINT,
    minimum_increment BIGINT
    latest_msg_id BIGINT
);"""


async def load_auction_cache(bot: discord.Client):
    try:
        auctions = await fetch_all_auctions(bot)
        for auction in auctions:
            channel_id = auction["channel_id"]
            auction_cache[channel_id] = {
                "channel_name": auction["channel_name"],
                "host_id": auction["host_id"],
                "host_name": auction["host_name"],
                "pokemon": auction["pokemon"],
                "highest_bidder_id": auction["highest_bidder_id"],
                "highest_bidder": auction["highest_bidder"],
                "highest_offer": auction["highest_offer"],
                "autobuy": auction["autobuy"],
                "ends_on": auction["ends_on"],
                "accepted_list": auction["accepted_list"],
                "image_link": auction["image_link"],
                "broadcast_msg_id": auction["broadcast_msg_id"],
                "market_value": auction["market_value"],
                "minimum_increment": auction["minimum_increment"],
                "last_minute_pinged": auction.get("last_minute_pinged", False),
                "is_bulk": auction.get("is_bulk", False),
            }
        # pretty_log("cache", f"Auction cache loaded with {len(auction_cache)} auctions")

    except Exception as e:
        pretty_log("error", f"Error loading auction cache: {e}", include_trace=True)


def get_auction_cache(channel_id: int):
    return auction_cache.get(channel_id, None)


async def check_cache_and_reload_if_missing(bot: discord.Client):
    """Checks if the auction cache is empty, and reloads it from the database if so."""
    if not auction_cache:
        pretty_log("cache", "Auction cache is empty, reloading from database...")
        await load_auction_cache(bot)
        if not auction_cache:
            pretty_log("warn", "Auction cache is still empty after reload attempt.")
            return False
    return True


def if_user_has_ongoing_auction_cache(user: discord.Member) -> bool:
    """Checks if the user has an ongoing auction in the cache,
    If server booster role they are allowed to have 2 ongoing auctions"""
    ongoing_auctions_count = 0
    max_auctions_allowed = 1
    if GRAND_LINE_AUCTION_ROLES.server_booster in [role.id for role in user.roles]:
        max_auctions_allowed = 2
    for auction in auction_cache.values():
        if auction["host_id"] == user.id:
            ongoing_auctions_count += 1
            if ongoing_auctions_count >= max_auctions_allowed:
                return True, max_auctions_allowed, ongoing_auctions_count
    return False, max_auctions_allowed, ongoing_auctions_count


def upsert_auction_cache(
    channel_id: int,
    channel_name: str,
    host_id: int,
    host_name: str,
    pokemon: str,
    highest_bidder_id: int,
    highest_bidder: str,
    highest_offer: int,
    autobuy: int,
    ends_on: int,
    accepted_list: str,
    image_link: str,
    broadcast_msg_id: int,
    market_value: int,
    minimum_increment: int,
    last_minute_pinged: bool = False,
    is_bulk: bool = False,
):
    try:
        auction_cache[channel_id] = {
            "channel_name": channel_name,
            "host_id": host_id,
            "host_name": host_name,
            "pokemon": pokemon,
            "highest_bidder_id": highest_bidder_id,
            "highest_bidder": highest_bidder,
            "highest_offer": highest_offer,
            "autobuy": autobuy,
            "ends_on": ends_on,
            "accepted_list": accepted_list,
            "image_link": image_link,
            "broadcast_msg_id": broadcast_msg_id,
            "market_value": market_value,
            "minimum_increment": minimum_increment,
            "last_minute_pinged": last_minute_pinged,
            "is_bulk": is_bulk,
        }

        def update_last_minute_pinged_cache(channel_id: int, last_minute_pinged: bool):
            try:
                if channel_id in auction_cache:
                    auction_cache[channel_id]["last_minute_pinged"] = last_minute_pinged
                    pretty_log(
                        "cache",
                        f"Auction cache last_minute_pinged updated for channel_id {channel_id} (New Value: {last_minute_pinged})",
                    )
                else:
                    pretty_log(
                        "warning",
                        f"Tried to update auction cache last_minute_pinged for channel_id {channel_id} but it was not found.",
                    )
            except Exception as e:
                pretty_log(
                    "error",
                    f"Error updating auction cache last_minute_pinged: {e}",
                    include_trace=True,
                )

        pretty_log(
            "cache",
            f"Auction cache upserted for channel_id {channel_id} (Pokemon: {pokemon}, Highest Offer: {highest_offer})",
        )

    except Exception as e:
        pretty_log("error", f"Error upserting auction cache: {e}", include_trace=True)


def update_auction_cache(
    channel_id: int, highest_bidder_id: int, highest_bidder: str, highest_offer: int
):
    try:
        if channel_id in auction_cache:
            auction_cache[channel_id]["highest_bidder_id"] = highest_bidder_id
            auction_cache[channel_id]["highest_bidder"] = highest_bidder
            auction_cache[channel_id]["highest_offer"] = highest_offer
            pretty_log(
                "cache",
                f"Auction cache updated for channel_id {channel_id} (Highest Offer: {highest_offer})",
            )
        else:
            pretty_log(
                "warning",
                f"Tried to update auction cache for channel_id {channel_id} but it was not found.",
            )

    except Exception as e:
        pretty_log("error", f"Error updating auction cache: {e}", include_trace=True)


def update_accept_list_cache(channel_id: int, accepted_list: str):
    try:
        if channel_id in auction_cache:
            auction_cache[channel_id]["accepted_list"] = accepted_list
            pretty_log(
                "cache",
                f"Auction cache accepted list updated for channel_id {channel_id} (Accepted List: {accepted_list})",
            )
        else:
            pretty_log(
                "warning",
                f"Tried to update auction cache accepted list for channel_id {channel_id} but it was not found.",
            )

    except Exception as e:
        pretty_log(
            "error",
            f"Error updating auction cache accepted list: {e}",
            include_trace=True,
        )


def is_there_ongoing_auction_cache(channel_id: int) -> bool:
    if channel_id in auction_cache:
        return True
    else:
        return False


def update_auction_cache_broadcast_msg_id(channel_id: int, broadcast_msg_id: int):
    try:
        if channel_id in auction_cache:
            auction_cache[channel_id]["broadcast_msg_id"] = broadcast_msg_id
            pretty_log(
                "cache",
                f"Auction cache broadcast message ID updated for channel_id {channel_id} (Broadcast Msg ID: {broadcast_msg_id})",
            )
        else:
            pretty_log(
                "warning",
                f"Tried to update auction cache broadcast message ID for channel_id {channel_id} but it was not found.",
            )

    except Exception as e:
        pretty_log(
            "error",
            f"Error updating auction cache broadcast message ID: {e}",
            include_trace=True,
        )


def update_auction_ends_on_cache(channel_id: int, ends_on: int):
    try:
        if channel_id in auction_cache:
            auction_cache[channel_id]["ends_on"] = ends_on
            pretty_log(
                "cache",
                f"Auction cache end time updated for channel_id {channel_id} (New Ends On: {ends_on})",
            )
        else:
            pretty_log(
                "warning",
                f"Tried to update auction cache end time for channel_id {channel_id} but it was not found.",
            )

    except Exception as e:
        pretty_log(
            "error", f"Error updating auction cache end time: {e}", include_trace=True
        )


def delete_auction_cache(channel_id: int):
    if channel_id in auction_cache:
        del auction_cache[channel_id]
        pretty_log("cache", f"Auction cache deleted for channel_id {channel_id}")


def update_last_minute_pinged_cache(channel_id: int, last_minute_pinged: bool):
    try:
        if channel_id in auction_cache:
            auction_cache[channel_id]["last_minute_pinged"] = last_minute_pinged
            pretty_log(
                "cache",
                f"Auction cache last_minute_pinged updated for channel_id {channel_id} (New Value: {last_minute_pinged})",
            )
        else:
            pretty_log(
                "warning",
                f"Tried to update auction cache last_minute_pinged for channel_id {channel_id} but it was not found.",
            )
    except Exception as e:
        pretty_log(
            "error",
            f"Error updating auction cache last_minute_pinged: {e}",
            include_trace=True,
        )
