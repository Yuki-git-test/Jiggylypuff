import discord

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
    minimum_increment BIGINT,
    last_minute_pinged BOOLEAN,
    is_bulk BOOLEAN DEFAULT FALSE
);"""


async def upsert_auction(
    bot: discord.Client,
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
        async with bot.pg_pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO auctions (channel_id, channel_name, host_id, host_name, pokemon, highest_bidder_id, highest_bidder, highest_offer, autobuy, ends_on, accepted_list, image_link, broadcast_msg_id, market_value, minimum_increment, last_minute_pinged, is_bulk)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, $16, $17)
                ON CONFLICT (channel_id) DO UPDATE SET
                    channel_name = EXCLUDED.channel_name,
                    host_id = EXCLUDED.host_id,
                    host_name = EXCLUDED.host_name,
                    pokemon = EXCLUDED.pokemon,
                    highest_bidder_id = EXCLUDED.highest_bidder_id,
                    highest_bidder = EXCLUDED.highest_bidder,
                    highest_offer = EXCLUDED.highest_offer,
                    autobuy = EXCLUDED.autobuy,
                    ends_on = EXCLUDED.ends_on,
                    accepted_list = EXCLUDED.accepted_list,
                    image_link = EXCLUDED.image_link,
                    broadcast_msg_id = EXCLUDED.broadcast_msg_id,
                    market_value = EXCLUDED.market_value,
                    minimum_increment = EXCLUDED.minimum_increment,
                    last_minute_pinged = EXCLUDED.last_minute_pinged,
                    is_bulk = EXCLUDED.is_bulk;
                """,
                channel_id,
                channel_name,
                host_id,
                host_name,
                pokemon,
                highest_bidder_id,
                highest_bidder,
                highest_offer,
                autobuy,
                ends_on,
                accepted_list,
                image_link,
                broadcast_msg_id,
                market_value,
                minimum_increment,
                last_minute_pinged,
                is_bulk,
            )
            pretty_log(
                "db",
                f"Auction upserted for channel_id {channel_id} (Pokemon: {pokemon}, Highest Offer: {highest_offer})",
            )
            # Update cache as well
            from utils.cache.auction_cache import upsert_auction_cache

            upsert_auction_cache(
                channel_id=channel_id,
                channel_name=channel_name,
                host_id=host_id,
                host_name=host_name,
                pokemon=pokemon,
                highest_bidder_id=highest_bidder_id,
                highest_bidder=highest_bidder,
                highest_offer=highest_offer,
                autobuy=autobuy,
                ends_on=ends_on,
                accepted_list=accepted_list,
                image_link=image_link,
                broadcast_msg_id=broadcast_msg_id,
                market_value=market_value,
                minimum_increment=minimum_increment,
                last_minute_pinged=last_minute_pinged,
                is_bulk=is_bulk,
            )
    except Exception as e:
        pretty_log("error", f"Error upserting auction: {e}", include_trace=True)


async def update_auction_bid(
    bot: discord.Client,
    channel_id: int,
    highest_bidder_id: int,
    highest_bidder: str,
    highest_offer: int,
    broadcast_msg_id: int = None,
    last_minute_pinged: bool = None,
):
    try:
        async with bot.pg_pool.acquire() as conn:
            if broadcast_msg_id is not None and last_minute_pinged is not None:
                await conn.execute(
                    """
                    UPDATE auctions
                    SET highest_bidder_id = $1, highest_bidder = $2, highest_offer = $3, broadcast_msg_id = $4, last_minute_pinged = $5
                    WHERE channel_id = $6;
                    """,
                    highest_bidder_id,
                    highest_bidder,
                    highest_offer,
                    broadcast_msg_id,
                    last_minute_pinged,
                    channel_id,
                )
            elif broadcast_msg_id is not None:
                await conn.execute(
                    """
                    UPDATE auctions
                    SET highest_bidder_id = $1, highest_bidder = $2, highest_offer = $3, broadcast_msg_id = $4
                    WHERE channel_id = $5;
                    """,
                    highest_bidder_id,
                    highest_bidder,
                    highest_offer,
                    broadcast_msg_id,
                    channel_id,
                )
            elif last_minute_pinged is not None:
                await conn.execute(
                    """
                    UPDATE auctions
                    SET highest_bidder_id = $1, highest_bidder = $2, highest_offer = $3, last_minute_pinged = $4
                    WHERE channel_id = $5;
                    """,
                    highest_bidder_id,
                    highest_bidder,
                    highest_offer,
                    last_minute_pinged,
                    channel_id,
                )
            else:
                await conn.execute(
                    """
                    UPDATE auctions
                    SET highest_bidder_id = $1, highest_bidder = $2, highest_offer = $3
                    WHERE channel_id = $4;
                    """,
                    highest_bidder_id,
                    highest_bidder,
                    highest_offer,
                    channel_id,
                )
            pretty_log(
                "db",
                f"Auction bid updated for channel_id {channel_id} (New Highest Offer: {highest_offer} by {highest_bidder})",
            )

    except Exception as e:
        pretty_log("error", f"Error updating auction bid: {e}", include_trace=True)


async def remove_accepted_list(bot: discord.Client, channel_id: int):
    try:
        async with bot.pg_pool.acquire() as conn:
            await conn.execute(
                """
                UPDATE auctions
                SET accepted_list = NULL
                WHERE channel_id = $1;
                """,
                channel_id,
            )
            pretty_log(
                "db",
                f"Auction accepted list removed for channel_id {channel_id}",
            )
            # Update cache as well
            from utils.cache.auction_cache import update_accept_list_cache

            update_accept_list_cache(channel_id, None)
    except Exception as e:
        pretty_log(
            "error", f"Error removing auction accepted list: {e}", include_trace=True
        )


async def update_accepted_list(
    bot: discord.Client,
    channel_id: int,
    accepted_list: str,
):
    try:
        async with bot.pg_pool.acquire() as conn:
            await conn.execute(
                """
                UPDATE auctions
                SET accepted_list = $1
                WHERE channel_id = $2;
                """,
                accepted_list,
                channel_id,
            )
            pretty_log(
                "db",
                f"Auction accepted list updated for channel_id {channel_id} (New Accepted List: {accepted_list})",
            )
            # Update cache as well
            from utils.cache.auction_cache import update_accept_list_cache

            update_accept_list_cache(channel_id, accepted_list)
    except Exception as e:
        pretty_log(
            "error", f"Error updating auction accepted list: {e}", include_trace=True
        )


async def update_ends_on(
    bot: discord.Client,
    channel_id: int,
    ends_on: int,
    broadcast_msg_id: int = None,
):
    try:
        async with bot.pg_pool.acquire() as conn:
            if broadcast_msg_id is not None:
                await conn.execute(
                    """
                    UPDATE auctions
                    SET ends_on = $1, broadcast_msg_id = $2
                    WHERE channel_id = $3;
                    """,
                    ends_on,
                    broadcast_msg_id,
                    channel_id,
                )
            else:
                await conn.execute(
                    """
                    UPDATE auctions
                    SET ends_on = $1
                    WHERE channel_id = $2;
                    """,
                    ends_on,
                    channel_id,
                )
            pretty_log(
                "db",
                f"Auction end time updated for channel_id {channel_id} (New Ends On: {ends_on})",
            )
            # Update cache as well
            from utils.cache.auction_cache import update_auction_ends_on_cache

            update_auction_ends_on_cache(channel_id, ends_on)

    except Exception as e:
        pretty_log("error", f"Error updating auction end time: {e}", include_trace=True)


async def update_last_minute_pinged(
    bot: discord.Client,
    channel_id: int,
    last_minute_pinged: bool,
):
    try:
        async with bot.pg_pool.acquire() as conn:
            await conn.execute(
                """
                UPDATE auctions
                SET last_minute_pinged = $1
                WHERE channel_id = $2;
                """,
                last_minute_pinged,
                channel_id,
            )
        pretty_log(
            "db",
            f"Auction last_minute_pinged updated for channel_id {channel_id} (New Value: {last_minute_pinged})",
        )
    except Exception as e:
        pretty_log(
            "error", f"Error updating last_minute_pinged: {e}", include_trace=True
        )


async def update_broadcast_msg_id(
    bot: discord.Client,
    channel_id: int,
    broadcast_msg_id: int,
):
    try:
        async with bot.pg_pool.acquire() as conn:
            await conn.execute(
                """
                UPDATE auctions
                SET broadcast_msg_id = $1
                WHERE channel_id = $2;
                """,
                broadcast_msg_id,
                channel_id,
            )
            pretty_log(
                "db",
                f"Auction broadcast message ID updated for channel_id {channel_id} (New Broadcast Msg ID: {broadcast_msg_id})",
            )
            # Update cache as well
            from utils.cache.auction_cache import update_auction_cache_broadcast_msg_id

            update_auction_cache_broadcast_msg_id(channel_id, broadcast_msg_id)

    except Exception as e:
        pretty_log(
            "error",
            f"Error updating auction broadcast message ID: {e}",
            include_trace=True,
        )


async def delete_auction(
    bot: discord.Client,
    channel_id: int,
):
    try:
        async with bot.pg_pool.acquire() as conn:
            await conn.execute(
                """
                DELETE FROM auctions
                WHERE channel_id = $1;
                """,
                channel_id,
            )
            pretty_log("db", f"Auction deleted for channel_id {channel_id}")
            # Delete from cache as well
            from utils.cache.auction_cache import delete_auction_cache

            delete_auction_cache(channel_id)

    except Exception as e:
        pretty_log("error", f"Error deleting auction: {e}", include_trace=True)


async def fetch_all_due_auctions(bot: discord.Client):
    try:
        async with bot.pg_pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT * FROM auctions
                WHERE ends_on <= CAST(EXTRACT(EPOCH FROM NOW()) AS BIGINT);
                """
            )

            return rows
    except Exception as e:
        pretty_log("error", f"Error fetching due auctions: {e}", include_trace=True)
        return []


async def fetch_auction_by_channel_id(bot: discord.Client, channel_id: int):
    try:
        async with bot.pg_pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT * FROM auctions
                WHERE channel_id = $1;
                """,
                channel_id,
            )
            if row:
                pretty_log(
                    "db",
                    f"Auction data fetched for channel_id {channel_id} (Pokemon: {row['pokemon']}, Highest Offer: {row['highest_offer']})",
                )
            else:
                pretty_log("db", f"No auction found for channel_id {channel_id}")
            return row
    except Exception as e:
        pretty_log(
            "error", f"Error fetching auction by channel_id: {e}", include_trace=True
        )
        return None


async def fetch_all_auctions(bot: discord.Client):
    try:
        async with bot.pg_pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT * FROM auctions;
                """
            )
            """pretty_log(
                "db",
                f"Fetched all auctions from the database (Total: {len(rows)}).",
            )"""
            return rows
    except Exception as e:
        pretty_log("error", f"Error fetching all auctions: {e}", include_trace=True)
        return []


async def set_last_minute_pinged(bot: discord.Client, channel_id: int, value: bool):
    try:
        async with bot.pg_pool.acquire() as conn:
            await conn.execute(
                """
                UPDATE auctions
                SET last_minute_pinged = $1
                WHERE channel_id = $2;
                """,
                value,
                channel_id,
            )
            pretty_log(
                "db",
                f"Auction last_minute_pinged set to {value} for channel_id {channel_id}",
            )
            # Update cache as well
            from utils.cache.auction_cache import update_last_minute_pinged_cache

            update_last_minute_pinged_cache(channel_id, value)
    except Exception as e:
        pretty_log(
            "error", f"Error setting last_minute_pinged: {e}", include_trace=True
        )


async def fetch_auctions_ending_within_10_mins(bot: discord.Client):
    # Grabs auctions that are ending within the next 10 minutes and haven't been pinged yet
    try:
        async with bot.pg_pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT * FROM auctions
                WHERE ends_on <= CAST(EXTRACT(EPOCH FROM NOW()) AS BIGINT) + 600
                AND last_minute_pinged = FALSE;
                """
            )

            return rows
    except Exception as e:
        pretty_log(
            "error",
            f"Error fetching auctions ending within 10 minutes: {e}",
            include_trace=True,
        )
        return []
