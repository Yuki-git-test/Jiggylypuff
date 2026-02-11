import re
import time
from datetime import datetime

import discord
from discord.ext import commands
from discord.ui import Button, View

from constants.grand_line_auction_constants import DEFAULT_EMBED_COLOR, KHY_CHANNEL_ID
from constants.paldea_galar_dict import get_dex_number_by_name
from constants.rarity import RARITY_MAP, get_rarity, in_game_mons_list
from utils.cache.cache_list import market_value_cache
from utils.db.market_value_db import fetch_market_value_cache
from utils.essentials.minimum_increment import format_names_for_market_value_lookup
from utils.logs.debug_log import debug_log, enable_debug
from utils.logs.pretty_log import pretty_log
from utils.visuals.pretty_defer import pretty_defer


# 🌸───────────────────────────────────────────────🌸
# 🩷 ⏰ Paginator        🩷
# 🌸───────────────────────────────────────────────🌸
class Paginator(View):
    def __init__(self, pages, timeout=180):
        super().__init__(timeout=timeout)
        self.pages = pages
        self.current_page = 0

        # Remove buttons if only one page
        if len(pages) <= 1:
            for item in self.children:
                item.disabled = True

    async def update_page(self, interaction):
        await interaction.response.edit_message(
            embed=self.pages[self.current_page], view=self
        )

    @discord.ui.button(label="Previous", style=discord.ButtonStyle.secondary)
    async def previous_button(self, interaction: discord.Interaction, button: Button):
        if self.current_page > 0:
            self.current_page -= 1
            await self.update_page(interaction)

    @discord.ui.button(label="Next", style=discord.ButtonStyle.secondary)
    async def next_button(self, interaction: discord.Interaction, button: Button):
        if self.current_page < len(self.pages) - 1:
            self.current_page += 1
            await self.update_page(interaction)


async def market_value_filter_func(bot: commands.Bot, interaction: discord.Interaction):
    """Filters in game mons with no market value data."""
    loader = await pretty_defer(
        interaction=interaction,
        content="Fetching market value data...",
        ephemeral=False,
    )

    if not market_value_cache:
        await loader.error(
            content="Market value data is currently unavailable. Please try again later."
        )
        return
    total_in_game_mons = len(in_game_mons_list)
    pretty_log(
        "info",
        f"Total in-game mons to filter: {total_in_game_mons} mons found.",
    )

    filtered_mons = []
    no_value_mons = []
    priority_no_value_mons = []
    low_priority_no_value_mons = []
    for mon in in_game_mons_list:
        dex = get_dex_number_by_name(mon)
        dex_str = dex if dex is not None else "N/A"
        formatted_name = format_names_for_market_value_lookup(mon)
        mon_str = f"{mon} #{dex_str}"
        if formatted_name in market_value_cache:
            filtered_mons.append(mon_str)
        else:
            # Check rarity and prioritize golden, shiny, mega, gmax, shiny mega, and shiny gmax mons in the no value list
            rarity = get_rarity(mon)
            if rarity in [
                "golden",
                "shiny",
                "mega",
                "gmax",
                "smega",
                "sgmax",
            ]:
                priority_no_value_mons.append(mon_str)
            else:
                low_priority_no_value_mons.append(mon_str)
            no_value_mons = priority_no_value_mons + low_priority_no_value_mons

    if len(no_value_mons) == 0:
        await loader.success(
            content="All in-game Pokémon have market value data. Great job!"
        )
        return

    # Embed
    no_value_mons_str = (
        "\n".join(no_value_mons)
        if no_value_mons
        else "All in-game mons have market value data."
    )

    no_value_mons_count = len(no_value_mons)
    pretty_log(
        "market_value_filter",
        f"Filtered in-game mons without market value data: {no_value_mons_count} mons found.",
    )
    # show 5 sample mons for debugging
    pretty_log(
        "debug",
        f"Sample mons without market value data: {no_value_mons[:5]}",
    )

    # Split mons into multiple embeds
    embeds = []
    chunk = []
    chunk_size = 0
    max_embed_size = 4096  # Discord embed description limit
    for mon in no_value_mons:
        mon_line = mon + "\n"
        # If adding this mon would exceed the embed limit, flush the chunk first
        if chunk_size > 0 and (chunk_size + len(mon_line)) > max_embed_size:
            embed = discord.Embed(
                title="In Game Pokemons without Market Value Data",
                description="".join(chunk),
                color=DEFAULT_EMBED_COLOR,
            )
            embed.set_footer(
                text=f"{no_value_mons_count} mons without market value data."
            )
            embeds.append(embed)
            chunk = []
            chunk_size = 0
        chunk.append(mon_line)
        chunk_size += len(mon_line)
    # Flush any remaining chunk
    if chunk:
        embed = discord.Embed(
            title="In Game Pokemons without Market Value Data",
            description="".join(chunk),
            color=DEFAULT_EMBED_COLOR,
        )
        embed.set_footer(text=f"{no_value_mons_count} mons without market value data.")
        embeds.append(embed)

    try:
        pretty_log("info", f"Paginator will send {len(embeds)} embeds.")
        await loader.success(
            content="",
            embed=embeds[0],
            view=Paginator(embeds),
            ephemeral=False,
        )
    except Exception as e:
        debug_log(f"Error sending market value filter embeds: {e}")
        await loader.error(
            content="An error occurred while displaying the market value filter results."
        )
        pretty_log("error", f"Error sending market value filter embeds: {e}")
