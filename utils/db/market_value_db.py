# 🟣────────────────────────────────────────────
#        Market Value DB Functions for Mew (bot.pg_pool)
# 🟣────────────────────────────────────────────
import re
from datetime import datetime

import discord
from discord import app_commands

from utils.cache.cache_list import market_value_cache, pokemon_list_cache
from utils.logs.debug_log import debug_log, enable_debug
from utils.logs.pretty_log import pretty_log


# (raw_name, normalized_name, display_name, dex_number)
POKEMON_AUTOCOMPLETE_INDEX: list[tuple[str, str, str, int]] = []


def normalize_pokemon_search_text(value: str) -> str:
    return re.sub(r"[^\w\s]", "", value.lower()).replace(" ", "")


def rebuild_pokemon_autocomplete_index() -> None:
    POKEMON_AUTOCOMPLETE_INDEX.clear()
    POKEMON_AUTOCOMPLETE_INDEX.extend(
        (
            name,
            normalize_pokemon_search_text(name),
            format_display_name_for_autocomplete(name),
            dex,
        )
        for name, dex in pokemon_list_cache.items()
    )
    debug_log(
        f"Built POKEMON_AUTOCOMPLETE_INDEX with {len(POKEMON_AUTOCOMPLETE_INDEX)} entries"
    )


def format_display_name_for_autocomplete(raw_name: str) -> str:
    SPECIAL_CASES = {
        "jangmo-o": "Jangmo-o",
        "hakamo-o": "Hakamo-o",
        "kommo-o": "Kommo-o",
        "tapu-koko": "Tapu-Koko",
        "tapu-lele": "Tapu-Lele",
        "tapu-bulu": "Tapu-Bulu",
        "tapu-fini": "Tapu-Fini",
    }

    clean_name = raw_name.lower()

    if "mega-" in clean_name:
        clean_name = clean_name.replace("mega-", "mega ")

    if clean_name in SPECIAL_CASES:
        return SPECIAL_CASES[clean_name]

    def smart_capitalize(name: str) -> str:
        return " ".join(
            "-".join(sub.capitalize() for sub in part.split("-"))
            for part in name.split()
        )

    return smart_capitalize(clean_name)


# ==================== 🌟 Autocomplete Functions ==================== #
async def pokemon_autocomplete(
    interaction: discord.Interaction, current: str
) -> list[app_commands.Choice[str]]:
    """
    Autocomplete Pokémon names with #Dex display.
    Matches both names and dex numbers.
    Uses a precomputed autocomplete index from pokemon_list_cache.
    """
    debug_log(f"Autocomplete input: '{current}'")

    # Recover gracefully if autocomplete gets called before cache load.
    if not POKEMON_AUTOCOMPLETE_INDEX and pokemon_list_cache:
        rebuild_pokemon_autocomplete_index()

    current_simple = normalize_pokemon_search_text(current or "")
    debug_log(f"Normalized input: '{current_simple}'")

    results_with_name: list[tuple[str, app_commands.Choice[str]]] = []
    seen = set()

    # Check if input looks numeric (dex search)
    dex_query = None
    if current_simple.isdigit():
        try:
            dex_query = int(current_simple)
            debug_log(f"Parsed dex_query: {dex_query}")
        except ValueError:
            debug_log("Failed to parse dex_query")
            dex_query = None

    for name, norm, display_name, dex in POKEMON_AUTOCOMPLETE_INDEX:
        if len(results_with_name) >= 25:
            break

        # Match by name
        if not current_simple or current_simple in norm:
            display = f"{display_name} #{dex}"
            if display not in seen:
                results_with_name.append(
                    (display_name, app_commands.Choice(name=display, value=name))
                )
                seen.add(display)

        # Match by dex number
        if dex_query is not None and dex_query == dex:
            display = f"{display_name} #{dex}"
            if display not in seen:
                results_with_name.append(
                    (display_name, app_commands.Choice(name=display, value=name))
                )
                seen.add(display)

    if not results_with_name:
        debug_log("No matches found")
        results_with_name.append(
            ("", app_commands.Choice(name="No matches found", value=current or ""))
        )

    debug_log(f"Returning {len(results_with_name)} results")
    # Sort alphabetically by display name
    results_with_name.sort(key=lambda x: x[0])
    return [choice for _, choice in results_with_name]


# 🍩────────────────────────────────────────────
#        💤 Pokemon List Names
# 🍩────────────────────────────────────────────
def build_pokemon_list_from_cache():
    """
    Build a dictionary mapping Pokémon names to their dex numbers
    using the global pokemon_cache.
    """
    if not market_value_cache:
        pretty_log("cache", "⚠️ Pokémon cache is empty, cannot build list.")
        return {}

    pokemon_list_cache.clear()
    pokemon_list_cache.update(
        {entry["pokemon"]: entry["dex_number"] for entry in market_value_cache.values()}
    )
    rebuild_pokemon_autocomplete_index()
    pretty_log(
        "cache", f"✅ Built Pokémon list with {len(pokemon_list_cache)} entries."
    )
    return pokemon_list_cache


async def update_rarity(bot, pokemon_name: str, rarity: str):
    """
    Update the rarity for a Pokémon in the market value table.
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
                    message=f"No market value row found for {pokemon_name}, skipping rarity update.",
                )
                return
            await conn.execute(
                "UPDATE market_value SET rarity = $1, last_updated = $2 WHERE pokemon_name = $3",
                rarity,
                datetime.utcnow(),
                pokemon_name,
            )
            # Update in cache as well
            if pokemon_name in market_value_cache:
                market_value_cache[pokemon_name]["rarity"] = rarity

        pretty_log(
            tag="db",
            message=f"Updated rarity for {pokemon_name} to {rarity}",
        )

    except Exception as e:
        pretty_log(
            tag="error",
            message=f"Failed to update rarity for {pokemon_name}: {e}",
        )


def fetch_rarity_cache(pokemon_name: str):
    """
    Get rarity for a Pokémon from cache.
    Returns 'unknown' if not found or no data.
    """
    pokemon_data = market_value_cache.get(pokemon_name.lower())
    if pokemon_data:
        return pokemon_data.get("rarity", "unknown")
    return "unknown"


def fetch_dex_number_cache(pokemon_name: str):
    """
    Get dex number for a Pokémon from cache.
    Returns 0 if not found or no data.
    """
    pokemon_data = market_value_cache.get(pokemon_name.lower())
    if pokemon_data:
        return pokemon_data.get("dex_number", 0)
    return 0


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


def fetch_pokemon_exclusivity_cache(pokemon_name: str):
    """
    Get exclusivity status for a Pokémon from cache.
    Returns False if not found or no data.
    """
    pokemon_data = market_value_cache.get(pokemon_name.lower())
    if pokemon_data:
        return pokemon_data.get("is_exclusive", False)
    return False


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


async def fetch_image_link_from_db(bot, pokemon_name: str):
    """
    Get image link for a Pokémon from database.
    Returns None if not found or no data.
    """
    try:
        async with bot.pg_pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT image_link FROM market_value WHERE pokemon_name = $1",
                pokemon_name.lower(),
            )
            return row["image_link"] if row and row["image_link"] else None
    except Exception as e:
        pretty_log(
            tag="error",
            message=f"Failed to fetch image link for {pokemon_name} from database: {e}",
        )
        return None


async def fetch_dex_number_from_db(bot, pokemon_name: str):
    """
    Get dex number for a Pokémon from database.
    Returns 0 if not found or no data.
    """
    try:
        async with bot.pg_pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT dex_number FROM market_value WHERE pokemon_name = $1",
                pokemon_name.lower(),
            )
            return row["dex_number"] if row and row["dex_number"] else 0
    except Exception as e:
        pretty_log(
            tag="error",
            message=f"Failed to fetch dex number for {pokemon_name} from database: {e}",
        )
        return 0


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
    image_link: str = None,
    rarity: str = "unknown",
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
                    current_listing, true_lowest, listing_seen, image_link, last_updated, rarity
                )
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
                ON CONFLICT (pokemon_name) DO UPDATE SET
                    dex_number = $2,
                    is_exclusive = $3,
                    lowest_market = $4,
                    current_listing = $5,
                    true_lowest = LEAST($6, market_value.true_lowest),
                    listing_seen = COALESCE($7, market_value.listing_seen),
                    image_link = COALESCE($8, market_value.image_link),
                    last_updated = $9,
                    rarity = COALESCE($10, market_value.rarity)
                """,
                pokemon_name.lower(),
                dex_number,
                is_exclusive,
                lowest_market,
                current_listing,
                true_lowest,
                listing_seen,
                image_link,
                datetime.utcnow(),
                rarity,
            )

        pretty_log(
            tag="db",
            message=f"Updated market value for {pokemon_name}: true_lowest={true_lowest:,}",
        )

    except Exception as e:
        pretty_log(
            tag="error",
            message=f"Failed to set market value for {pokemon_name}: {e}",
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
    image_link: str = None,
    is_exclusive: bool = None,
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
            if image_link is not None and is_exclusive is not None:
                await conn.execute(
                    """
                    INSERT INTO market_value (
                        pokemon_name, lowest_market, listing_seen, last_updated, current_listing, image_link, is_exclusive
                    )
                    VALUES ($1, $2, $3, $4, $5, $6, $7)
                    ON CONFLICT (pokemon_name) DO UPDATE SET
                        lowest_market = $2,
                        listing_seen = $3,
                        last_updated = $4,
                        current_listing = $5,
                        image_link = $6,
                        is_exclusive = $7
                    """,
                    pokemon_name,
                    lowest_market,
                    listing_seen,
                    datetime.utcnow(),
                    current_listing,
                    image_link,
                    is_exclusive,
                )
            elif image_link is not None:
                await conn.execute(
                    """
                    INSERT INTO market_value (
                        pokemon_name, lowest_market, listing_seen, last_updated, current_listing, image_link
                    )
                    VALUES ($1, $2, $3, $4, $5, $6)
                    ON CONFLICT (pokemon_name) DO UPDATE SET
                        lowest_market = $2,
                        listing_seen = $3,
                        last_updated = $4,
                        current_listing = $5,
                        image_link = $6
                    """,
                    pokemon_name,
                    lowest_market,
                    listing_seen,
                    datetime.utcnow(),
                    current_listing,
                    image_link,
                )
            elif is_exclusive is not None:
                await conn.execute(
                    """
                    INSERT INTO market_value (
                        pokemon_name, lowest_market, listing_seen, last_updated, current_listing, is_exclusive
                    )
                    VALUES ($1, $2, $3, $4, $5, $6)
                    ON CONFLICT (pokemon_name) DO UPDATE SET
                        lowest_market = $2,
                        listing_seen = $3,
                        last_updated = $4,
                        current_listing = $5,
                        is_exclusive = $6
                    """,
                    pokemon_name,
                    lowest_market,
                    listing_seen,
                    datetime.utcnow(),
                    current_listing,
                    is_exclusive,
                )
            else:
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
                if image_link is not None:
                    market_value_cache[pokemon_name]["image_link"] = image_link
                if is_exclusive is not None:
                    market_value_cache[pokemon_name]["is_exclusive"] = is_exclusive
                pretty_log(
                    tag="cache",
                    message=f"Updated market value for {pokemon_name} via listener: lowest_market={lowest_market:,}, listing_seen={listing_seen}, current_listing={current_listing:,}"
                    + (f", image_link updated" if image_link is not None else "")
                    + (f", is_exclusive updated" if is_exclusive is not None else ""),
                )
            else:
                market_value_cache[pokemon_name] = {
                    "pokemon": pokemon_name,
                    "lowest_market": lowest_market,
                    "listing_seen": listing_seen,
                    "current_listing": current_listing,
                    "image_link": image_link if image_link is not None else None,
                    "is_exclusive": is_exclusive if is_exclusive is not None else False,
                }
                pretty_log(
                    tag="cache",
                    message=f"Added new market value for {pokemon_name} via listener: lowest_market={lowest_market:,}, listing_seen={listing_seen}, current_listing={current_listing:,}"
                    + (f", image_link set" if image_link is not None else "")
                    + (f", is_exclusive set" if is_exclusive is not None else ""),
                )
        pretty_log(
            tag="db",
            message=f"Updated market value for {pokemon_name} via listener: lowest_market={lowest_market:,}, listing_seen={listing_seen}, current_listing={current_listing:,}"
            + (f", image_link updated" if image_link is not None else "")
            + (f", is_exclusive updated" if is_exclusive is not None else ""),
        )
    except Exception as e:
        pretty_log(
            tag="error",
            message=f"Failed to update market value for {pokemon_name} via listener: {e}",
        )


async def update_dex_number(bot, pokemon_name: str, dex_number: int):
    """
    Update the dex number for a Pokémon in the market value table.
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
                    message=f"No market value row found for {pokemon_name}, skipping dex number update.",
                )
                return
            await conn.execute(
                "UPDATE market_value SET dex_number = $1, last_updated = $2 WHERE pokemon_name = $3",
                dex_number,
                datetime.utcnow(),
                pokemon_name,
            )
            # Update in cache as well
            if pokemon_name in market_value_cache:
                market_value_cache[pokemon_name]["dex_number"] = dex_number

        pretty_log(
            tag="db",
            message=f"Updated dex number for {pokemon_name} to {dex_number}",
        )

    except Exception as e:
        pretty_log(
            tag="error",
            message=f"Failed to update dex number for {pokemon_name}: {e}",
        )


async def upsert_image_link(
    bot, pokemon_name: str, image_link: str, is_exclusive: bool = None
):
    """
    Upsert the image link for a Pokémon in the market value table.
    """
    pokemon_name = pokemon_name.lower()
    try:
        async with bot.pg_pool.acquire() as conn:
            if is_exclusive is not None:
                await conn.execute(
                    """
                    INSERT INTO market_value (pokemon_name, image_link, last_updated, is_exclusive)
                    VALUES ($1, $2, $3, $4)
                    ON CONFLICT (pokemon_name) DO UPDATE SET
                        image_link = $2,
                        last_updated = $3,
                        is_exclusive = $4
                    """,
                    pokemon_name,
                    image_link,
                    datetime.utcnow(),
                    is_exclusive,
                )
            else:
                await conn.execute(
                    """
                    INSERT INTO market_value (pokemon_name, image_link, last_updated)
                    VALUES ($1, $2, $3)
                    ON CONFLICT (pokemon_name) DO UPDATE SET
                        image_link = $2,
                        last_updated = $3
                    """,
                    pokemon_name,
                    image_link,
                    datetime.utcnow(),
                )
            # Update in cache as well
            if pokemon_name in market_value_cache:
                market_value_cache[pokemon_name]["image_link"] = image_link
                if is_exclusive is not None:
                    market_value_cache[pokemon_name]["is_exclusive"] = is_exclusive
            else:
                market_value_cache[pokemon_name] = {
                    "pokemon": pokemon_name,
                    "image_link": image_link,
                    "is_exclusive": is_exclusive if is_exclusive is not None else False,
                }

        pretty_log(
            tag="db",
            message=f"Upserted image link for {pokemon_name}"
            + (
                f", is_exclusive set to {is_exclusive}"
                if is_exclusive is not None
                else ""
            ),
        )

    except Exception as e:
        pretty_log(
            tag="error",
            message=f"Failed to upsert image link for {pokemon_name}: {e}",
        )


async def update_image_link(
    bot, pokemon_name: str, image_link: str, is_exclusive: bool = None
):
    """
    Update the image link for a Pokémon in the market value table.
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
                    message=f"No market value row found for {pokemon_name}, skipping image link update.",
                )
                return
            if is_exclusive is not None:
                await conn.execute(
                    "UPDATE market_value SET image_link = $1, last_updated = $2, is_exclusive = $3 WHERE pokemon_name = $4",
                    image_link,
                    datetime.utcnow(),
                    is_exclusive,
                    pokemon_name,
                )
            else:
                await conn.execute(
                    "UPDATE market_value SET image_link = $1, last_updated = $2 WHERE pokemon_name = $3",
                    image_link,
                    datetime.utcnow(),
                    pokemon_name,
                )
            # Update in cache as well
            if pokemon_name in market_value_cache:
                market_value_cache[pokemon_name]["image_link"] = image_link
                if is_exclusive is not None:
                    market_value_cache[pokemon_name]["is_exclusive"] = is_exclusive

        pretty_log(
            tag="db",
            message=f"Updated image link for {pokemon_name}"
            + (
                f", is_exclusive set to {is_exclusive}"
                if is_exclusive is not None
                else ""
            ),
        )

    except Exception as e:
        pretty_log(
            tag="error",
            message=f"Failed to update image link for {pokemon_name}: {e}",
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
        )

    except Exception as e:
        pretty_log(
            tag="error",
            message=f"Failed to upsert market value for {pokemon_name}: {e}",
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
        )

    except Exception as e:
        pretty_log(
            tag="error",
            message=f"Failed to update is_exclusive for {pokemon_name}: {e}",
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
        )
        return True
    except Exception as e:
        pretty_log(
            tag="error",
            message=f"Failed to cleanup old market data: {e}",
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
                        current_listing, true_lowest, listing_seen, last_updated, rarity, image_link
                    )
                    VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
                    ON CONFLICT (pokemon_name) DO UPDATE SET
                        dex_number = $2,
                        is_exclusive = $3,
                        lowest_market = $4,
                        current_listing = $5,
                        true_lowest = LEAST($6, market_value.true_lowest),
                        listing_seen = COALESCE($7, market_value.listing_seen),
                        last_updated = $8,
                        rarity = COALESCE($9, market_value.rarity),
                        image_link = COALESCE($10, market_value.image_link)
                    """,
                    pokemon_name.lower(),
                    data.get("dex_number", 0),
                    data.get("is_exclusive", False),
                    data.get("lowest_market", 0),
                    data.get("current_listing", 0),
                    data.get("true_lowest", 0),
                    data.get("listing_seen", "Unknown"),
                    datetime.utcnow(),
                    data.get("rarity", "unknown"),
                    data.get("image_link", None),
                )
                update_count += 1

        pretty_log(
            tag="db",
            message=f"Synced {update_count} market value entries to database",
        )
        return True

    except Exception as e:
        pretty_log(
            tag="error",
            message=f"Failed to sync market cache to database: {e}",
        )
        return False


async def check_and_load_market_cache(bot) -> dict:
    """
    Check if market value cache is loaded, if not load from database.
    """
    if not market_value_cache:
        await load_market_cache_from_db(bot)
        if not market_value_cache:
            pretty_log(
                tag="error",
                message="Market value cache is empty after loading from database.",
            )
    return market_value_cache


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
                    "dex_number": row["dex_number"],
                    "is_exclusive": row.get("is_exclusive", False),
                    "lowest_market": row["lowest_market"],
                    "current_listing": row["current_listing"],
                    "true_lowest": row["true_lowest"],
                    "listing_seen": row["listing_seen"],
                    "image_link": row.get("image_link", None),
                    "rarity": row.get("rarity", "unknown"),
                }

        """pretty_log(
            tag="",
            message=f"Loaded {len(cache)} market value entries from database",
            label="💎 Market Value Cache",

        )"""
        market_value_cache.update(cache)  # Update the global cache
        build_pokemon_list_from_cache()  # Build the pokemon list cache based on market value cache
        return market_value_cache, pokemon_list_cache

    except Exception as e:
        pretty_log(
            tag="error",
            message=f"Failed to load market cache from database: {e}",
        )
        return {}
