from constants.grand_line_auction_constants import (
    GRAND_LINE_AUCTION_CATEGORIES,
    GRAND_LINE_AUCTION_EMOJIS,
    GRAND_LINE_AUCTION_ROLES,
)
from utils.db.market_value_db import (
    fetch_market_value_cache,
    is_pokemon_exclusive_cache,
)
from utils.essentials.minimum_increment import (
    compute_maximum_auction_duration_seconds,
    compute_minimum_increment,
    format_names_for_market_value_lookup,
)
from utils.logs.debug_log import debug_log, enable_debug

from .pokemons import *


class Rarity_Colors:
    golden = 0xFDDC2B
    smega = 0x693D54
    sgmax = 0xCD1882
    shiny = 0xFF99CC
    gmax = 0xA30B46
    mega = 0x000000
    legendary = 0xA007F8
    super_rare = 0xF8F407
    exclusive = 0xEA260B
    uncommon = 0x13B4E7
    common = 0x0855FB
    bulk = 0x3DDDC5


RARITY_MAP = {
    "common": {
        "color": Rarity_Colors.common,
        "emoji": GRAND_LINE_AUCTION_EMOJIS.common,
        "auction role": [],
    },
    "uncommon": {
        "color": Rarity_Colors.uncommon,
        "emoji": GRAND_LINE_AUCTION_EMOJIS.uncommon,
        "auction role": [],
    },
    "rare": {
        "color": Rarity_Colors.super_rare,
        "emoji": GRAND_LINE_AUCTION_EMOJIS.rare,
        "auction role": [],
    },
    "super rare": {
        "color": Rarity_Colors.super_rare,
        "emoji": GRAND_LINE_AUCTION_EMOJIS.superrare,
        "auction role": [],
    },
    "legendary": {
        "color": Rarity_Colors.legendary,
        "emoji": GRAND_LINE_AUCTION_EMOJIS.legendary,
        "auction role": [GRAND_LINE_AUCTION_ROLES.legendary_auction],
        "increment value": 20_000,
        "category": [GRAND_LINE_AUCTION_CATEGORIES.LEGENDARY_AUCTION],
    },
    "mega": {
        "color": Rarity_Colors.mega,
        "emoji": GRAND_LINE_AUCTION_EMOJIS.mega,
        "auction role": [GRAND_LINE_AUCTION_ROLES.mega_auction],
        "increment value": 50_000,
        "category": [GRAND_LINE_AUCTION_CATEGORIES.MEGA_AUCTION],
    },
    "gmax": {
        "color": Rarity_Colors.gmax,
        "emoji": GRAND_LINE_AUCTION_EMOJIS.gigantamax,
        "auction role": [GRAND_LINE_AUCTION_ROLES.gmax_auction],
        "increment value": 100_000,
        "category": [GRAND_LINE_AUCTION_CATEGORIES.GIGANTAMAX_AUCTION],
    },
    "shiny": {
        "color": Rarity_Colors.shiny,
        "emoji": GRAND_LINE_AUCTION_EMOJIS.shiny,
        "auction role": [GRAND_LINE_AUCTION_ROLES.shiny_auction],
        "increment value": 50_000,
        "category": [GRAND_LINE_AUCTION_CATEGORIES.SHINY_AUCTION],
    },
    "sgmax": {
        "color": Rarity_Colors.sgmax,
        "emoji": GRAND_LINE_AUCTION_EMOJIS.shinygigantamax,
        "auction role": [
            GRAND_LINE_AUCTION_ROLES.shiny_auction,
            GRAND_LINE_AUCTION_ROLES.gmax_auction,
        ],
        "increment value": 100_000,
        "category": [
            GRAND_LINE_AUCTION_CATEGORIES.SHINY_AUCTION,
            GRAND_LINE_AUCTION_CATEGORIES.GIGANTAMAX_AUCTION,
        ],
    },
    "smega": {
        "color": Rarity_Colors.smega,
        "emoji": GRAND_LINE_AUCTION_EMOJIS.shinymega,
        "auction role": [
            GRAND_LINE_AUCTION_ROLES.shiny_auction,
            GRAND_LINE_AUCTION_ROLES.mega_auction,
        ],
        "increment value": 50_000,
        "category": [
            GRAND_LINE_AUCTION_CATEGORIES.SHINY_AUCTION,
            GRAND_LINE_AUCTION_CATEGORIES.MEGA_AUCTION,
        ],
    },
    "golden": {
        "color": Rarity_Colors.golden,
        "emoji": GRAND_LINE_AUCTION_EMOJIS.golden,
        "auction role": [GRAND_LINE_AUCTION_ROLES.golden_auction],
        "increment value": 100_000,
        "category": [GRAND_LINE_AUCTION_CATEGORIES.GOLDEN_AUCTION],
    },
    "exclusive": {
        "color": Rarity_Colors.exclusive,
        "auction role": [GRAND_LINE_AUCTION_ROLES.exclusive_auction],
        "increment value": 30_000,
        "category": [GRAND_LINE_AUCTION_CATEGORIES.EXCLUSIVE_AUCTIONS],
    },
    "bulk": {
        "color": Rarity_Colors.bulk,
        "auction role": [GRAND_LINE_AUCTION_ROLES.bulk_auction],
        "category": [GRAND_LINE_AUCTION_CATEGORIES.BULK_AUCTION],
    },
}


def get_rarity(pokemon: str):
    """Determines the rarity of a given Pokemon based on the name"""

    name = pokemon.lower()
    if "golden" in name:
        return "golden"
    elif "shiny" in name and "gigantamax" in name:
        return "sgmax"
    elif "shiny" in name and "mega" in name:
        return "smega"
    elif "shiny" in name:
        return "shiny"
    elif "gigantamax" in name:
        return "gmax"
    elif "mega" in name and not "yanmega" in name and not "meganium" in name:
        return "mega"

    # Fallback to the list (case-insensitive)
    elif name in (mon.lower() for mon in legendary_mons):
        return "legendary"
    elif name in (mon.lower() for mon in superrare_mons):
        return "super rare"
    elif name in (mon.lower() for mon in rare_mons):
        return "rare"
    elif name in (mon.lower() for mon in uncommon_mons):
        return "uncommon"
    elif name in (mon.lower() for mon in common_mons):
        return "common"
    else:
        return None


auctionable_mons_list = (
    list(legendary_mons.keys())
    + list(superrare_mons.keys())
    + list(rare_mons.keys())
    + list(uncommon_mons.keys())
    + list(common_mons.keys())
    + list(exclusive_mons.keys())
)
in_game_mons_list = (
    auctionable_mons_list
    + list(shiny_mons.keys())
    + list(golden_mons.keys())
    + list(mega_mons.keys())
    + list(gigantamax_mons.keys())
    + list(shiny_mega_mons.keys())
    + list(shiny_gigantamax_mons.keys())
)
exclusive_mons_list = list(exclusive_mons.keys())


# enable_debug(f"{__name__}.is_mon_exclusive")
def is_mon_exclusive(pokemon: str) -> bool:
    """
    Checks if a given Pokémon is exclusive based on the exclusive_mons list or the market value cache.
    """
    debug_log(f"Checking exclusivity for: {pokemon}")
    name = pokemon.lower()
    if any(name == mon.lower() for mon in exclusive_mons_list):
        debug_log(f"{pokemon} is exclusive based on the exclusive_mons list.")
        return True
    # Check cache for exclusivity, if it's exclusive then it's not auctionable
    pokemon = format_names_for_market_value_lookup(pokemon)
    if is_pokemon_exclusive_cache(pokemon):
        debug_log(f"{pokemon} is exclusive based on the market value cache.")
        return True
    else:
        debug_log(f"{pokemon} is not exclusive based on the market value cache.")
        return False


enable_debug(f"{__name__}.is_mon_auctionable")


def is_mon_auctionable(pokemon: str) -> bool:
    """
    Checks if a given Pokémon is auctionable based on whether it has been released in the game.
    Gigantamax and Mega Pokémon are always auctionable except golden variants.
    Golden and Shiny variants are auctionable only if present in their respective lists.
    """
    name = pokemon.lower()
    debug_log(f"Checking if '{pokemon}' is auctionable.")

    # Gigantamax and Mega Pokémon are always auctionable except golden variants
    if ("gigantamax" in name or "mega" in name) and "golden" not in name:
        debug_log(f"'{pokemon}' is Gigantamax or Mega (not golden): auctionable.")
        return True

    # Golden variant: check golden_mons list
    if "golden" in name:
        result = any(name == mon.lower() for mon in golden_mons)
        debug_log(f"'{pokemon}' is golden. Auctionable: {result}")
        return result

    # Shiny variant: check shiny_mons list
    if "shiny" in name:
        result = any(name == mon.lower() for mon in shiny_mons)
        debug_log(f"'{pokemon}' is shiny. Auctionable: {result}")
        if not result:
            # Check exclusives list
            result = any(name == mon.lower() for mon in exclusive_mons)
            debug_log(
                f"'{pokemon}' is shiny but not in shiny list. Checking exclusives. Auctionable: {result}"
            )

        return result

    # Fallback: check general auctionable list
    if any(name == mon.lower() for mon in auctionable_mons_list):
        debug_log(f"'{pokemon}' found in general auctionable list.")
        return True
    # Check cache for market value, if it exists then it's auctionable
    pokemon_lookup = format_names_for_market_value_lookup(pokemon)
    market_value = fetch_market_value_cache(pokemon_lookup)
    if market_value is not None:
        debug_log(f"'{pokemon}' has market value ({market_value}): auctionable.")
        return True
    debug_log(f"'{pokemon}' is not auctionable.")
    return False
