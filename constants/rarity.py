from constants.grand_line_auction_constants import (
    GRAND_LINE_AUCTION_CATEGORIES,
    GRAND_LINE_AUCTION_EMOJIS,
    GRAND_LINE_AUCTION_ROLES,
)
from utils.db.market_value_db import fetch_market_value_cache
from utils.essentials.minimum_increment import (
    compute_maximum_auction_duration_seconds,
    compute_minimum_increment,
    format_names_for_market_value_lookup,
)
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
    },
    "mega": {
        "color": Rarity_Colors.mega,
        "emoji": GRAND_LINE_AUCTION_EMOJIS.mega,
        "auction role": [GRAND_LINE_AUCTION_ROLES.mega_auction],
        "increment value": 50_000,
    },
    "gmax": {
        "color": Rarity_Colors.gmax,
        "emoji": GRAND_LINE_AUCTION_EMOJIS.gigantamax,
        "auction role": [GRAND_LINE_AUCTION_ROLES.gmax_auction],
        "increment value": 100_000,
    },
    "shiny": {
        "color": Rarity_Colors.shiny,
        "emoji": GRAND_LINE_AUCTION_EMOJIS.shiny,
        "auction role": [GRAND_LINE_AUCTION_ROLES.shiny_auction],
        "increment value": 50_000,
    },
    "sgmax": {
        "color": Rarity_Colors.sgmax,
        "emoji": GRAND_LINE_AUCTION_EMOJIS.shinygigantamax,
        "auction role": [
            GRAND_LINE_AUCTION_ROLES.shiny_auction,
            GRAND_LINE_AUCTION_ROLES.gmax_auction,
        ],
        "increment value": 100_000,
    },
    "smega": {
        "color": Rarity_Colors.smega,
        "emoji": GRAND_LINE_AUCTION_EMOJIS.shinymega,
        "auction role": [
            GRAND_LINE_AUCTION_ROLES.shiny_auction,
            GRAND_LINE_AUCTION_ROLES.mega_auction,
        ],
        "increment value": 50_000,
    },
    "golden": {
        "color": Rarity_Colors.golden,
        "emoji": GRAND_LINE_AUCTION_EMOJIS.golden,
        "auction role": [GRAND_LINE_AUCTION_ROLES.golden_auction],
        "increment value": 100_000,
    },
    "exclusive": {
        "color": Rarity_Colors.exclusive,
        "auction role": [GRAND_LINE_AUCTION_ROLES.exclusive_auction],
        "increment value": 30_000,
    },
    "bulk": {
        "color": Rarity_Colors.bulk,
        "auction role": [GRAND_LINE_AUCTION_ROLES.bulk_auction],
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
    elif "mega" in name:
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
)


def is_mon_auctionable(pokemon: str) -> bool:
    """
    Checks if a given Pokémon is auctionable based on whether it has been released in the game.
    Gigantamax and Mega Pokémon are always auctionable except golden variants.
    Golden and Shiny variants are auctionable only if present in their respective lists.
    """
    name = pokemon.lower()

    # Gigantamax and Mega Pokémon are always auctionable except golden variants
    if ("gigantamax" in name or "mega" in name) and "golden" not in name:
        return True

    # Golden variant: check golden_mons list
    if "golden" in name:
        return any(name == mon.lower() for mon in golden_mons)

    # Shiny variant: check shiny_mons list
    if "shiny" in name:
        return any(name == mon.lower() for mon in shiny_mons)

    # Fallback: check general auctionable list
    if any(name == mon.lower() for mon in auctionable_mons_list):
        return True
    # Check cache for market value, if it exists then it's auctionable
    pokemon = format_names_for_market_value_lookup(pokemon)
    market_value = fetch_market_value_cache(pokemon)
    if market_value is not None:
        return True
    return False
