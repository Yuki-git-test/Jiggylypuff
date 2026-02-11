# inside get_pokemon_gif.py
from typing import Literal

from constants.paldea_galar_dict import get_dex_number_by_name
from constants.pokemon_gifs import *
from utils.db.market_value_db import fetch_image_link_cache
from utils.essentials.minimum_increment import format_names_for_market_value_lookup
from utils.logs.debug_log import debug_log, enable_debug
from utils.logs.pretty_log import pretty_log

enable_debug(f"{__name__}.get_pokemon_gif")
hyphen_mon_names = [
    "jangmo-o",
    "hakamo-o",
    "kommo-o",
    "tapu-koko",
    "tapu-lele",
    "tapu-bulu",
    "tapu-fini",
]


def get_pokemon_gif(input_name: str):
    """
    Returns the pokemon gif
    """
    formatted_name = format_names_for_market_value_lookup(input_name)
    # First try to get from cache
    cached_link = fetch_image_link_cache(formatted_name)
    if cached_link:
        pretty_log(
            tag="debug",
            message=f"Found cached image link for '{formatted_name}': {cached_link}",
        )
        return cached_link

    original_input = input_name
    shiny = False
    golden = False
    form: Literal["regular", "mega", "gmax"] = "regular"
    region_suffix = ""
    debug_log(f"Input Pokémon name: {input_name}")
    # Normalize input
    name_parts = input_name.lower().replace("_", "-").split()
    debug_log(f"Normalized name_parts: {name_parts}")
    dex_number = None
    if "golden" in name_parts:
        golden = True
        name_parts.remove("golden")
        debug_log("Detected 'golden' in name_parts, setting golden=True")

    if "shiny" in name_parts:
        shiny = True
        name_parts.remove("shiny")
        debug_log("Detected 'shiny' in name_parts, setting shiny=True")

    remaining_name = "-".join(name_parts)
    debug_log(f"Remaining name after removing shiny/golden: {remaining_name}")

    regions = {
        "alolan": "-alola",
        "galarian": "-galar",
        "hisuian": "-hisui",
        "paldean": "-paldea",
    }
    for region_prefix, suffix in regions.items():
        if remaining_name.startswith(region_prefix + "-"):
            region_suffix = suffix
            debug_log(
                f"Detected region prefix '{region_prefix}', applying suffix '{suffix}' and stripping prefix from remaining_name."
            )
            remaining_name = remaining_name[len(region_prefix) + 1 :]
            break

    if remaining_name.startswith("mega-"):
        form = "mega"
        debug_log("Detected 'mega-' prefix, setting form='mega'")
        remaining_name = remaining_name.replace("mega-", "")
    elif remaining_name.startswith(("gigantamax-", "gmax-")):
        form = "gmax"
        debug_log("Detected 'gigantamax-' or 'gmax-' prefix, setting form='gmax'")
        remaining_name = remaining_name.replace("gigantamax-", "").replace("gmax-", "")

    # 🔹 Special gmax aliases
    gmax_aliases = {
        "urshifu-rapidstrike": "urs",
        "urshifu-singlestrike": "uss",
        "eternamax-eternatus": "eternatus",
    }
    if form == "gmax" and remaining_name in gmax_aliases:
        debug_log(
            f"Gmax alias detected for '{remaining_name}', replacing with '{gmax_aliases[remaining_name]}'"
        )
        remaining_name = gmax_aliases[remaining_name]

    base_name = f"{remaining_name}{region_suffix}".lower()
    debug_log(f"Base name for sprites: {base_name}")
    # Remove "shiny" and "golden" from the input for comparison
    compare_name = (
        input_name.lower()
        .replace("shiny", "")
        .replace("golden", "")
        .replace("_", "-")
        .strip()
    )
    compare_name = " ".join(compare_name.split())  # Remove extra spaces
    if compare_name in hyphen_mon_names:
        base_name = base_name.replace("-", "")

    attr_name = remaining_name.replace("-", "_")
    debug_log(f"Attribute name for URL lookup: {attr_name}")

    gif_url = None

    # 🔹 Golden check (priority)
    if golden:
        # Remove Golden from name and normalize for dex lookup
        golden_base_name = (
            original_input.lower().replace("golden", "").replace("_", "-").strip()
        )
        golden_base_name = "-".join(
            golden_base_name.split()
        )  # Replace spaces with hyphens
        golden_base_name_attr = golden_base_name.replace("-", "_")
        debug_log(f"Golden base name for dex lookup: {golden_base_name}")
        dex_number = get_dex_number_by_name(golden_base_name)
        debug_log(f"Dex number for golden form: {dex_number}")
        pretty_log(
            tag="debug",
            message=(
                f"Golden form detected. Looking up dex number for '{golden_base_name}': {dex_number}"
            ),
        )
        if form == "mega":
            golden_attr_name = f"mega_{attr_name}"
            gif_url = getattr(GOLDEN_MEGA_POKEMON_URL, golden_attr_name, None)
            debug_log(
                f"Golden mega form: attr_name={golden_attr_name}, gif_url={gif_url}"
            )
        elif form == "gmax":
            gif_url = getattr(GOLDEN_POKEMON_URL, f"gmax_{attr_name}", None)
            debug_log(
                f"Golden gmax form: attr_name=gmax_{attr_name}, gif_url={gif_url}"
            )
        else:
            if dex_number:
                # Pad dex_number to 3 digits
                padded_dex = str(dex_number).zfill(3)
                gif_url = f"https://graphics.tppcrpg.net/xy/golden/{padded_dex}M.gif"
                debug_log(f"Golden regular form: direct gif_url={gif_url}")

            else:
                gif_url = getattr(GOLDEN_POKEMON_URL, golden_base_name_attr, None)
                debug_log(
                    f"Golden regular form: no dex number, fallback gif_url={gif_url}"
                )

    # 🔹 Shiny check (priority, same idea as golden)
    if shiny and not gif_url:
        if form == "mega":
            shiny_attr_name = f"mega_{attr_name}"
            gif_url = getattr(SHINY_POKEMON_URL, shiny_attr_name, None)
        elif form == "gmax":
            gif_url = getattr(SHINY_POKEMON_URL, f"gmax_{attr_name}", None)
        else:
            gif_url = getattr(SHINY_POKEMON_URL, attr_name, None)

    # 🔹 Fallbacks
    if not gif_url:
        if form == "gmax":
            gif_url = getattr(
                SHINY_GMAX_URL if shiny else REGULAR_GMAX_URL, attr_name, None
            )
        else:
            gif_url = getattr(REGULAR_POKEMON_URL, attr_name, None)

    # 🔹 Last resort → showdown sprite
    if not gif_url:
        shiny_prefix = "ani-shiny" if shiny else "xyani"
        suffix = "" if form == "regular" else f"-{form}"
        # Special handling for Mega Mewtwo and Mega Charizard forms
        if form == "mega":
            if base_name in ["mewtwo-y", "mewtwo-megay"]:
                gif_url = f"https://play.pokemonshowdown.com/sprites/{shiny_prefix}/mewtwo-megay.gif?quality=lossless"
            elif base_name in ["mewtwo-x", "mewtwo-megax"]:
                gif_url = f"https://play.pokemonshowdown.com/sprites/{shiny_prefix}/mewtwo-megax.gif?quality=lossless"
            elif base_name in ["charizard-x", "charizard-megax"]:
                gif_url = f"https://play.pokemonshowdown.com/sprites/{shiny_prefix}/charizard-megax.gif?quality=lossless"
            elif base_name in ["charizard-y", "charizard-megay"]:
                gif_url = f"https://play.pokemonshowdown.com/sprites/{shiny_prefix}/charizard-megay.gif?quality=lossless"
            else:
                gif_url = f"https://play.pokemonshowdown.com/sprites/{shiny_prefix}/{base_name}{suffix}.gif?quality=lossless"

        elif "primal" in base_name:
            # Make it groudon-primal or kyogre-primal
            if "groudon" in base_name:
                gif_url = f"https://play.pokemonshowdown.com/sprites/{shiny_prefix}/groudon-primal.gif?quality=lossless"
            elif "kyogre" in base_name:
                gif_url = f"https://play.pokemonshowdown.com/sprites/{shiny_prefix}/kyogre-primal.gif?quality=lossless"
            elif "dialga" in base_name:
                gif_url = REGULAR_POKEMON_URL.primal_dialga
        elif "ash-greninja" in base_name:
            gif_url = f"https://play.pokemonshowdown.com/sprites/{shiny_prefix}/greninja-ash.gif?quality=lossless"
        else:
            gif_url = f"https://play.pokemonshowdown.com/sprites/{shiny_prefix}/{base_name}{suffix}.gif?quality=lossless"

    gif_name = f"{'golden ' if golden else ''}{'shiny ' if shiny else ''}{form + ' ' if form != 'regular' else ''}{remaining_name}"

    error = None
    if not gif_url:
        error = f"Cannot find Pokemon GIF for '{original_input}'"

    pretty_log(
        tag="debug" if gif_url else "error",
        message=(f"Fetched GIF URL for '{gif_name}': {gif_url}" if gif_url else error),
    )
    return gif_url
