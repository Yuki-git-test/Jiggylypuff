from typing import Literal

import discord
from discord import app_commands
from discord.ext import commands

from utils.db.market_value_db import pokemon_autocomplete
from utils.essentials.command_safe import run_command_safe
from utils.essentials.role_checks import auctioneer_only
from utils.group_commands_func.market_value import *

GROUP_NAME = "market-value"


# 🎀────────────────────────────────────────────
#           🌸 Market Value Cog Setup 🌸
# ─────────────────────────────────────────────
class Market_Value_Group_Commands(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # 🎀────────────────────────────────────────────
    #           🌸 Slash Command Group 🌸
    # 🎀────────────────────────────────────────────
    market_value_group = app_commands.Group(
        name=GROUP_NAME, description="Commands related to market value"
    )

    # 🎀────────────────────────────────────────────
    #          🌸 /market-value view 🌸
    # 🎀────────────────────────────────────────────
    @market_value_group.command(
        name="view", description="View current market value for a Pokémon"
    )
    @app_commands.describe(
        pokemon="Name of the Pokémon (e.g. Pikachu, Charizard)",
    )
    @app_commands.autocomplete(pokemon=pokemon_autocomplete)
    @auctioneer_only()
    async def market_value_view(
        self,
        interaction: discord.Interaction,
        pokemon: str,
    ):
        slash_cmd_name = "market-value view"

        await run_command_safe(
            bot=self.bot,
            interaction=interaction,
            slash_cmd_name=slash_cmd_name,
            command_func=view_market_value_func,
            pokemon=pokemon,
        )

    market_value_view.extras = {"category": "Staff"}

    # 🎀────────────────────────────────────────────
    #          🌸 /market-value update 🌸
    # 🎀────────────────────────────────────────────
    @market_value_group.command(
        name="update", description="Update market value for a Pokémon"
    )
    @app_commands.describe(
        pokemon="Name of the Pokémon (e.g. Pikachu, Charizard)",
        amount="New market value (e.g. '1k', '1.5m')",
        is_pokemon_exclusive="Whether the Pokémon is event exclusive (true/false)",
        image_link="Optional image link for the Pokémon",
    )
    @app_commands.autocomplete(pokemon=pokemon_autocomplete)
    @auctioneer_only()
    async def market_value_update(
        self,
        interaction: discord.Interaction,
        pokemon: str,
        amount: str = None,
        is_pokemon_exclusive: bool = False,
        image_link: str = None,
    ):
        slash_cmd_name = "market-value update"

        await run_command_safe(
            bot=self.bot,
            interaction=interaction,
            slash_cmd_name=slash_cmd_name,
            command_func=update_market_value_func,
            pokemon=pokemon,
            amount=amount,
            is_pokemon_exclusive=is_pokemon_exclusive,
            image_link=image_link,
        )

    market_value_update.extras = {"category": "Staff"}

    # 🎀────────────────────────────────────────────
    #          🌸 /market-value filter 🌸
    # 🎀────────────────────────────────────────────
    @market_value_group.command(
        name="filter",
        description="Filter in-game Pokémon that do not have market value data",
    )
    @auctioneer_only()
    async def market_value_filter(self, interaction: discord.Interaction):
        slash_cmd_name = "market-value filter"

        await run_command_safe(
            bot=self.bot,
            interaction=interaction,
            slash_cmd_name=slash_cmd_name,
            command_func=market_value_filter_func,
        )

    market_value_filter.extras = {"category": "Staff"}


async def setup(bot: commands.Bot):
    await bot.add_cog(Market_Value_Group_Commands(bot))
