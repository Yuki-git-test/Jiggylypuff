# 🟣────────────────────────────────────────────
#        Market Value DB Functions for Mew (bot.pg_pool)
# 🟣────────────────────────────────────────────

from datetime import datetime

import discord

from utils.cache.cache_list import market_value_cache
from utils.logs.pretty_log import pretty_log


def fetch_market_value_cache(pokemon_name: str):
    """
    Get market value data for a specific Pokémon from cache.
    Returns dict with market data or None if not found.
    """
    return market_value_cache.get(pokemon_name.lower())


def fetch_lowest_market_value_cache(pokemon_name: str):
    """
    Get lowest market value for a Pokémon from cache.
    Returns 0 if not found or no data.
    """
    pokemon_data = market_value_cache.get(pokemon_name.lower())
    if pokemon_data:
        return pokemon_data.get("lowest_market", 0)
    return 0


def is_pokemon_exclusive_cache(pokemon_name: str):
    """
    Check if a Pokémon is exclusive based on cache data.
    Returns False if not found or no data.
    """
    pokemon_data = market_value_cache.get(pokemon_name.lower())
    if pokemon_data:
        return pokemon_data.get("is_exclusive", False)
    return False


def fetch_image_link_cache(pokemon_name: str):
    """
    Get image link for a Pokémon from cache.
    Returns None if not found or no data.
    """
    pokemon_data = market_value_cache.get(pokemon_name.lower())
    if pokemon_data:
        return pokemon_data.get("image_link", None)
    return None


# --------------------
#  Upsert market value data
# --------------------
async def set_market_value(
    bot,
    pokemon_name: str,
    dex_number: int,
    is_exclusive: bool = False,
    lowest_market: int = 0,
    current_listing: int = 0,
    true_lowest: int = 0,
    listing_seen: str | None = None,
):
    """
    Insert or update market value data for a Pokémon.
    """
    try:
        async with bot.pg_pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO market_value (
                    pokemon_name, dex_number, is_exclusive, lowest_market,
                    current_listing, true_lowest, listing_seen, last_updated
                )
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                ON CONFLICT (pokemon_name) DO UPDATE SET
                    dex_number = $2,
                    is_exclusive = $3,
                    lowest_market = $4,
                    current_listing = $5,
                    true_lowest = LEAST($6, market_value.true_lowest),
                    listing_seen = COALESCE($7, market_value.listing_seen),
                    last_updated = $8
                """,
                pokemon_name.lower(),
                dex_number,
                is_exclusive,
                lowest_market,
                current_listing,
                true_lowest,
                listing_seen,
                datetime.utcnow(),
            )

        pretty_log(
            tag="db",
            message=f"Updated market value for {pokemon_name}: true_lowest={true_lowest:,}",
            bot=bot,
        )

    except Exception as e:
        pretty_log(
            tag="error",
            message=f"Failed to set market value for {pokemon_name}: {e}",
            bot=bot,
        )
def fetch_image_link_cache(pokemon_name: str):
    """
    Get image link for a Pokémon from cache.
    Returns None if not found or no data.
    """
    pokemon_data = market_value_cache.get(pokemon_name.lower())
    if pokemon_data:
        return pokemon_data.get("image_link", None)
    return None

async def update_market_value_via_listener(
    bot,
    pokemon_name: str,
    lowest_market: int,
    listing_seen: str,
    current_listing: int = None,
):
    """
    Update market value data for a Pokémon based on market view listener input.if exists, else insert new record with minimal data
    Only updates lowest_market and listing_seen fields.
    """
    pokemon_name = pokemon_name.lower()
    if current_listing is None:
        current_listing = lowest_market
    try:
        async with bot.pg_pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO market_value (
                    pokemon_name, lowest_market, listing_seen, last_updated, current_listing
                )
                VALUES ($1, $2, $3, $4, $5)
                ON CONFLICT (pokemon_name) DO UPDATE SET
                    lowest_market = $2,
                    listing_seen = $3,
                    last_updated = $4,
                    current_listing = $5
                """,
                pokemon_name,
                lowest_market,
                listing_seen,
                datetime.utcnow(),
                current_listing,
            )
            # Update in cache as well
            if pokemon_name in market_value_cache:
                market_value_cache[pokemon_name]["lowest_market"] = lowest_market
                market_value_cache[pokemon_name]["listing_seen"] = listing_seen
                market_value_cache[pokemon_name]["current_listing"] = current_listing
                pretty_log(
                    tag="cache",
                    message=f"Updated market value for {pokemon_name} via listener: lowest_market={lowest_market:,}, listing_seen={listing_seen}, current_listing={current_listing:,}",
                    bot=bot,
                )
            else:
                market_value_cache[pokemon_name] = {
                    "pokemon": pokemon_name,
                    "lowest_market": lowest_market,
                    "listing_seen": listing_seen,
                    "current_listing": current_listing,
                }
                pretty_log(
                    tag="cache",
                    message=f"Added new market value for {pokemon_name} via listener: lowest_market={lowest_market:,}, listing_seen={listing_seen}, current_listing={current_listing:,}",
                    bot=bot,
                )
        pretty_log(
            tag="db",
            message=f"Updated market value for {pokemon_name} via listener: lowest_market={lowest_market:,}, listing_seen={listing_seen}, current_listing={current_listing:,}",
            bot=bot,
        )
    except Exception as e:
        pretty_log(
            tag="error",
            message=f"Failed to update market value for {pokemon_name} via listener: {e}",
            bot=bot,
        )


async def update_market_value(
    bot,
    pokemon_name: str,
    lowest_market: int,
    listing_seen: str,
    image_link: str = None,
    is_exclusive: bool = None,
):
    """
    Update specific fields of market value data for a Pokémon.
    """
    pokemon_name = pokemon_name.lower()
    try:
        async with bot.pg_pool.acquire() as conn:
            # Upsert logic: update if exists, else insert
            await conn.execute(
                """
                INSERT INTO market_value (
                    pokemon_name, lowest_market, listing_seen, last_updated, image_link, is_exclusive
                )
                VALUES ($1, $2, $3, $4, $5, $6)
                ON CONFLICT (pokemon_name) DO UPDATE SET
                    lowest_market = $2,
                    listing_seen = $3,
                    last_updated = $4
                    """
                + (", image_link = $5" if image_link is not None else "")
                + (", is_exclusive = $6" if is_exclusive is not None else "")
                + " WHERE market_value.pokemon_name = $1",
                pokemon_name,
                lowest_market,
                listing_seen,
                datetime.utcnow(),
                image_link if image_link is not None else None,
                is_exclusive if is_exclusive is not None else None,
            )
            # Update in cache as well
            if pokemon_name in market_value_cache:
                market_value_cache[pokemon_name]["lowest_market"] = lowest_market
                market_value_cache[pokemon_name]["listing_seen"] = listing_seen
                if image_link is not None:
                    market_value_cache[pokemon_name]["image_link"] = image_link
                # Only update is_exclusive if provided
                if is_exclusive is not None:
                    market_value_cache[pokemon_name]["is_exclusive"] = is_exclusive
            else:
                market_value_cache[pokemon_name] = {
                    "pokemon": pokemon_name,
                    "lowest_market": lowest_market,
                    "listing_seen": listing_seen,
                    "image_link": image_link if image_link is not None else None,
                    "is_exclusive": is_exclusive if is_exclusive is not None else False,
                }

        pretty_log(
            tag="db",
            message=f"Upserted market value for {pokemon_name}: lowest_market={lowest_market:,}, listing_seen={listing_seen}",
            bot=bot,
        )

    except Exception as e:
        pretty_log(
            tag="error",
            message=f"Failed to upsert market value for {pokemon_name}: {e}",
            bot=bot,
        )


async def update_is_exclusive(
    bot, pokemon_name: str, is_exclusive: bool, image_link: str = None
):
    """
    Update the is_exclusive field for a Pokémon in the market value table.
    """
    pokemon_name = pokemon_name.lower()
    try:
        async with bot.pg_pool.acquire() as conn:
            # Only update if row exists
            row = await conn.fetchrow(
                "SELECT pokemon_name FROM market_value WHERE pokemon_name = $1",
                pokemon_name,
            )
            if not row:
                pretty_log(
                    tag="db",
                    message=f"No market value row found for {pokemon_name}, skipping update.",
                    bot=bot,
                )
                return
            # Build update query
            update_fields = ["is_exclusive = $1", "last_updated = $2"]
            update_values = [is_exclusive, datetime.utcnow()]
            param_index = 3
            if image_link is not None:
                update_fields.insert(1, f"image_link = ${param_index}")
                update_values.append(image_link)
                param_index += 1
            update_query = f"UPDATE market_value SET {', '.join(update_fields)} WHERE pokemon_name = ${param_index}"
            update_values.append(pokemon_name)
            await conn.execute(update_query, *update_values)
            # Update in cache as well
            if pokemon_name in market_value_cache:
                market_value_cache[pokemon_name]["is_exclusive"] = is_exclusive
                if image_link is not None:
                    market_value_cache[pokemon_name]["image_link"] = image_link

        pretty_log(
            tag="db",
            message=f"Updated is_exclusive for {pokemon_name} to {is_exclusive}"
            + (f", image_link updated" if image_link is not None else ""),
            bot=bot,
        )

    except Exception as e:
        pretty_log(
            tag="error",
            message=f"Failed to update is_exclusive for {pokemon_name}: {e}",
            bot=bot,
        )


# --------------------
#  Fetch single Pokémon market value
# --------------------
async def fetch_market_value(bot, pokemon_name: str) -> dict | None:
    """
    Get market value data for a specific Pokémon.
    """
    try:
        async with bot.pg_pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT * FROM market_value WHERE pokemon_name = $1",
                pokemon_name.lower(),
            )
            return dict(row) if row else None
    except Exception as e:
        pretty_log(
            tag="error",
            message=f"Failed to fetch market value for {pokemon_name}: {e}",
            bot=bot,
        )
        return None


# --------------------
#  Fetch all market values
# --------------------
async def fetch_all_market_values(bot) -> list[dict]:
    """
    Return all market value data as list of dicts.
    """
    try:
        async with bot.pg_pool.acquire() as conn:
            rows = await conn.fetch(
                "SELECT * FROM market_value ORDER BY last_updated DESC"
            )
            return [dict(row) for row in rows]
    except Exception as e:
        pretty_log(
            tag="error",
            message=f"Failed to fetch market values: {e}",
            bot=bot,
        )
        return []


# --------------------
#  Fetch high value Pokémon (above threshold)
# --------------------
async def fetch_high_value_pokemon(bot, min_price: int = 100000) -> list[dict]:
    """
    Get Pokémon with true_lowest above specified threshold.
    """
    try:
        async with bot.pg_pool.acquire() as conn:
            rows = await conn.fetch(
                "SELECT * FROM market_value WHERE true_lowest >= $1 ORDER BY true_lowest DESC",
                min_price,
            )
            return [dict(row) for row in rows]
    except Exception as e:
        pretty_log(
            tag="error",
            message=f"Failed to fetch high value pokemon: {e}",
            bot=bot,
        )
        return []


# --------------------
#  Delete old market data
# --------------------
async def cleanup_old_market_data(bot, days_old: int = 30) -> bool:
    """
    Delete market value records older than specified days.
    """
    try:
        async with bot.pg_pool.acquire() as conn:
            result = await conn.execute(
                "DELETE FROM market_value WHERE last_updated < NOW() - INTERVAL '%s days'",
                days_old,
            )

        deleted_count = int(result.split()[-1]) if result.split() else 0
        pretty_log(
            tag="db",
            message=f"Cleaned up {deleted_count} old market value records",
            bot=bot,
        )
        return True
    except Exception as e:
        pretty_log(
            tag="error",
            message=f"Failed to cleanup old market data: {e}",
            bot=bot,
        )
        return False


# --------------------
#  Sync cache to database
# --------------------
async def sync_market_cache_to_db(bot, market_cache: dict):
    """
    Sync entire market value cache to database.
    """
    try:
        update_count = 0
        async with bot.pg_pool.acquire() as conn:
            for pokemon_name, data in market_cache.items():
                await conn.execute(
                    """
                    INSERT INTO market_value (
                        pokemon_name, dex_number, is_exclusive, lowest_market,
                        current_listing, true_lowest, listing_seen, last_updated
                    )
                    VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                    ON CONFLICT (pokemon_name) DO UPDATE SET
                        dex_number = $2,
                        is_exclusive = $3,
                        lowest_market = $4,
                        current_listing = $5,
                        true_lowest = LEAST($6, market_value.true_lowest),
                        listing_seen = COALESCE($7, market_value.listing_seen),
                        last_updated = $8
                    """,
                    pokemon_name.lower(),
                    data.get("dex", 0),
                    data.get("is_exclusive", False),
                    data.get("lowest_market", 0),
                    data.get("current_listing", 0),
                    data.get("true_lowest", 0),
                    data.get("listing_seen", "Unknown"),
                    datetime.utcnow(),
                )
                update_count += 1

        pretty_log(
            tag="db",
            message=f"Synced {update_count} market value entries to database",
            bot=bot,
        )
        return True

    except Exception as e:
        pretty_log(
            tag="error",
            message=f"Failed to sync market cache to database: {e}",
            bot=bot,
        )
        return False


# --------------------
#  Load database into cache
# --------------------
async def load_market_cache_from_db(bot) -> dict:
    """
    Load all market value data from database into cache format.
    """
    try:
        cache = {}
        async with bot.pg_pool.acquire() as conn:
            rows = await conn.fetch("SELECT * FROM market_value")

            for row in rows:
                cache[row["pokemon_name"]] = {
                    "pokemon": row["pokemon_name"],
                    "dex": row["dex_number"],
                    "is_exclusive": row.get("is_exclusive", False),
                    "lowest_market": row["lowest_market"],
                    "current_listing": row["current_listing"],
                    "true_lowest": row["true_lowest"],
                    "listing_seen": row["listing_seen"],
                    "image_link": row.get("image_link", None),
                }

        """pretty_log(
            tag="",
            message=f"Loaded {len(cache)} market value entries from database",
            label="💎 Market Value Cache",
            bot=bot,
        )"""
        return market_value_cache.update(cache)  # Update the global cache

    except Exception as e:
        pretty_log(
            tag="error",
            message=f"Failed to load market cache from database: {e}",
            bot=bot,
        )
        return {}
