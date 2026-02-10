import time
from datetime import datetime
from typing import Literal

import discord
from discord import app_commands
from discord.ext import commands

from utils.autocomplete.pokemon_autocomplete import pokemon_autocomplete
from utils.essentials.command_safe import run_command_safe
from utils.essentials.role_checks import auctioneer_only
from utils.group_commands_func.bulk import *
from utils.logs.pretty_log import pretty_log
from utils.parser.number_parser import parse_compact_number

GROUP_NAME = "test-bulk-auction"  # change to "auction" when done testing
# 🎀────────────────────────────────────────────
#           🌸 Bulk Cog Setup 🌸
# ─────────────────────────────────────────────


class BulkGroupCommand(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # 🎀────────────────────────────────────────────
    #           🌸 Slash Command Group 🌸
    # 🎀────────────────────────────────────────────
    bulk_group = app_commands.Group(
        name=GROUP_NAME, description="Commands related to bulk auctions"
    )

    # 🎀────────────────────────────────────────────
    #          🌸 /bulk-auction start 🌸
    # 🎀────────────────────────────────────────────
    @bulk_group.command(name="start", description="Starts a bulk auction")
    @app_commands.describe(
        pokemon="Names of the Pokémon (e.g. 2 Pikachu, Charizard)",
        duration="Auction duration (e.g. '5m', '3h')",
        autobuy="Autobuy price (e.g. '1k', '1.5m')",
        accepted_pokemon="Optional List of accepted Pokémon (comma-separated)",
    )
    async def auction_start(
        self,
        interaction: discord.Interaction,
        pokemon: str,
        duration: str,
        autobuy: str = None,
        accepted_pokemon: str = None,
    ):
        slash_cmd_name = "bulk-auction start"

        await run_command_safe(
            bot=self.bot,
            interaction=interaction,
            slash_cmd_name=slash_cmd_name,
            command_func=bulk_start_auction_func,
            pokemon=pokemon,
            duration=duration,
            autobuy=autobuy,
            accepted_pokemon=accepted_pokemon,
        )

    # 🎀────────────────────────────────────────────
    #          🌸 /bulk-auction list 🌸
    # 🎀────────────────────────────────────────────
    @bulk_group.command(
        name="list", description="Ends the active auction in this channel"
    )
    @auctioneer_only()
    async def auction_end(self, interaction: discord.Interaction):
        slash_cmd_name = "bulk-auction list"

        await run_command_safe(
            bot=self.bot,
            interaction=interaction,
            slash_cmd_name=slash_cmd_name,
            command_func=bulk_view_func,
        )


async def setup(bot: commands.Bot):
    await bot.add_cog(BulkGroupCommand(bot))
