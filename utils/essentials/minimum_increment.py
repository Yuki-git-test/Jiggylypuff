import discord


from utils.autocomplete.pokemon_autocomplete import format_price_w_coin
from utils.db.market_value_db import (
    fetch_lowest_market_value_cache,
    is_pokemon_exclusive_cache,
)
from utils.logs.debug_log import debug_log, enable_debug
from utils.logs.pretty_log import pretty_log

MIN_AUCTION_VALUE = 400_000
LOW_RARITIES = ["common", "uncommon", "rare", "super rare"]
RARITIES_WITH_VARRYING_INCREMENT = ["golden", "gmax", "sgmax", "golden mega"]
from utils.db.market_value_db import fetch_lowest_market_value_cache

#enable_debug(f"{__name__}.compute_minimum_increment")
#enable_debug(f"{__name__}.compute_maximum_auction_duration_seconds")
#enable_debug(f"{__name__}.compute_total_bulk_value")

def format_names_for_market_value_lookup(pokemon_name: str):
    """
    Format Pokémon name for market value lookup"""
    debug_log(f"input: {pokemon_name!r}")
    pokemon_name = pokemon_name.lower().strip()
    if pokemon_name.startswith("sgmax "):
        # shiny gigantamax-<name>
        base = pokemon_name[6:].strip()
        result = f"shiny gigantamax-{base}"
        debug_log(f"sgmax result: {result}")
        return result
    elif pokemon_name.startswith("gmax "):
        # gigantamax-<name>
        base = pokemon_name[5:].strip()
        result = f"gigantamax-{base}"
        debug_log(f"gmax result: {result}")
        return result
    elif "smega" in pokemon_name:
        result = pokemon_name.replace("smega", "shiny mega").replace("-", " ")
        debug_log(f"smega result: {result}")
        return result
    elif "mega" in pokemon_name:
        result = pokemon_name.replace("-", " ")
        debug_log(f"mega result: {result}")
        return result
    else:
        debug_log(f"default result: {pokemon_name}")
        return pokemon_name


def compute_total_bulk_value(pokemon_list):
    """
    Compute the total market value of a list of Pokémon.
    Expects pokemon_list as [(name, quantity), ...]
    """
    has_market_value = []
    has_no_market_value = []
    is_any_exclusive = False
    total_value = 0
    for pokemon_name, quantity in pokemon_list:
        pokemon_name = format_names_for_market_value_lookup(pokemon_name)
        market_value = fetch_lowest_market_value_cache(pokemon_name)
        if not is_any_exclusive:
            is_exclusive = is_pokemon_exclusive_cache(pokemon_name)
            if is_exclusive:
                is_any_exclusive = True
        if market_value is not None:
            debug_log(
                f"Market value for {pokemon_name}: {market_value:,} | Quantity: {quantity:,}"
            )
            total_value += market_value * quantity
            has_market_value.append((pokemon_name, quantity, market_value))
        else:
            has_no_market_value.append((pokemon_name, quantity, None))
    return total_value, has_market_value, has_no_market_value, is_any_exclusive

def compute_minimum_increment_for_bulk(
    total_bulk_value: int, rarity:str,  any_exclusive: bool
):
    """
    Compute the minimum increment for a Pokémon based on its rarity and current price.
    Uses the lowest market value from cache to determine increments.
    """
    from constants.rarity import RARITY_MAP

    debug_log(
        f"Called compute_minimum_increment with total_bulk_value={total_bulk_value}"
    )

    lowered_rarity = rarity.lower()
    if lowered_rarity in LOW_RARITIES:
        debug_log(f"Bulk is in LOW_RARITIES: {lowered_rarity}")
        # check if any exclusive
        if any_exclusive:
            return 30_000, None
        else:
            return 20_000, None

    default_increment = RARITY_MAP.get(rarity, {}).get("increment value", 50_000)
    debug_log(f"Default increment for rarity {rarity}: {default_increment}")
    if any(r in lowered_rarity for r in RARITIES_WITH_VARRYING_INCREMENT):
        debug_log(
            f"Bulk has a rarity with varying increment: {lowered_rarity}"
        )
        # Value from 20.001m to 100m = 250k increment
        if total_bulk_value <= 20_000_000 and total_bulk_value <= 100_000_000:
            debug_log(
                f"Lowest market value between 20,001,000 and 100,000,000. Returning 250000."
            )
            return 250_000, None
        # Value above 100m = 500k increment
        elif total_bulk_value > 100_000_000:
            debug_log(f"Lowest market value above 100,000,000. Returning 500000.")
            return 500_000, None

        elif total_bulk_value < MIN_AUCTION_VALUE and total_bulk_value > 0:
            debug_log(f"Lowest market value below MIN_AUCTION_VALUE. Returning 0.")
            return 0, "Pokemon value is below minimum auction value"
    else:
        debug_log(f"Returning default increment: {default_increment}")
        return default_increment, None


def compute_minimum_increment(
    pokemon_name: str, rarity: str, auction_type: str = "single"
):
    """
    Compute the minimum increment for a Pokémon based on its rarity and current price.
    Uses the lowest market value from cache to determine increments.
    """
    from constants.rarity import RARITY_MAP

    debug_log(
        f"Called compute_minimum_increment with pokemon_name={pokemon_name}, rarity={rarity}"
    )
    pokemon_name = format_names_for_market_value_lookup(pokemon_name)
    lowest_market_value = fetch_lowest_market_value_cache(pokemon_name)
    debug_log(f"Lowest market value for {pokemon_name}: {lowest_market_value}")
    if lowest_market_value is None:
        debug_log(
            f"No market value found for {pokemon_name}. Returning default increment."
        )
        return (
            0,
            "No market value yet, Ask staff to set a market value for this Pokemon",
        )
    elif lowest_market_value < MIN_AUCTION_VALUE:
        debug_log(
            f"Lowest market value for {pokemon_name} is below minimum auction value. Returning 0."
        )
        return (
            0,
            f"{pokemon_name}'s market value is {format_price_w_coin(lowest_market_value)}, Auction minimum value is {format_price_w_coin(MIN_AUCTION_VALUE)}",
        )
    lowest_market_value = fetch_lowest_market_value_cache(pokemon_name)
    debug_log(f"Lowest market value for {pokemon_name}: {lowest_market_value}")

    lowered_rarity = rarity.lower()
    if lowered_rarity in LOW_RARITIES:
        debug_log(f"{pokemon_name} is in LOW_RARITIES: {lowered_rarity}")
        # check if exclusive
        if is_pokemon_exclusive_cache(pokemon_name):
            if lowest_market_value < MIN_AUCTION_VALUE:
                debug_log(
                    f"{pokemon_name} is exclusive but lowest market value is below minimum auction value. Returning 0."
                )
                return (
                    0,
                    "Pokemon is exclusive but its market value is below minimum auction value (400k)",
                )
            else:
                debug_log(f"{pokemon_name} is exclusive. Returning 30000.")
                return 30_000, None
        else:
            debug_log(f"{pokemon_name} is not exclusive. Returning False.")
            return (
                None,
                "Pokemon is not auctionable because it's not exclusive and below Legendary rarity.",
            )

    default_increment = RARITY_MAP.get(rarity, {}).get("increment value", 50_000)
    debug_log(f"Default increment for rarity {rarity}: {default_increment}")
    if any(r in lowered_rarity for r in RARITIES_WITH_VARRYING_INCREMENT):
        debug_log(
            f"{pokemon_name} has a rarity with varying increment: {lowered_rarity}"
        )
        if lowest_market_value == 0:
            debug_log(
                f"Lowest market value is 0. Returning default increment: {default_increment}"
            )
            return default_increment, None
        # Value from 20.001m to 100m = 250k increment
        elif lowest_market_value <= 20_000_000 and lowest_market_value <= 100_000_000:
            debug_log(
                f"Lowest market value between 20,001,000 and 100,000,000. Returning 250000."
            )
            return 250_000, None
        # Value above 100m = 500k increment
        elif lowest_market_value > 100_000_000:
            debug_log(f"Lowest market value above 100,000,000. Returning 500000.")
            return 500_000, None

        elif lowest_market_value < MIN_AUCTION_VALUE and lowest_market_value > 0:
            debug_log(f"Lowest market value below MIN_AUCTION_VALUE. Returning 0.")
            return 0, "Pokemon value is below minimum auction value"
    else:
        debug_log(f"Returning default increment: {default_increment}")
        return default_increment, None


def compute_maximum_auction_duration_seconds(pokemon_value: int) -> int:
    """
    Compute the maximum auction duration in seconds based on the Pokémon's market value.
    """
    debug_log(f"Computing max auction duration for pokemon_value={pokemon_value:,}")
    # 400k to 1m = 1 hour
    if 400_000 <= pokemon_value <= 1_000_000:
        debug_log(
            "Pokemon value between 400,000 and 1,000,000. Returning 3600 seconds."
        )
        return 3_600
    # 1.001m to 5m = 2 hours
    elif 1_000_001 <= pokemon_value <= 5_000_000:
        debug_log(
            "Pokemon value between 1,000,001 and 5,000,000. Returning 7200 seconds."
        )
        return 7_200
    # 5.001m to 20m = 3 hours
    elif 5_000_001 <= pokemon_value <= 20_000_000:
        debug_log(
            "Pokemon value between 5,000,001 and 20,000,000. Returning 10800 seconds."
        )
        return 10_800
    # 20.001m to 150m = 4 hours
    elif 20_000_001 <= pokemon_value <= 150_000_000:
        debug_log(
            "Pokemon value between 20,000,001 and 150,000,000. Returning 14400 seconds."
        )
        return 14_400
    # Above 150m = 5 hours
    elif pokemon_value > 150_000_000:
        debug_log("Pokemon value above 150,000,000. Returning 18000 seconds.")
        return 18_000
    else:
        debug_log("Pokemon value below 400,000. Returning 0 seconds.")
        return 0
