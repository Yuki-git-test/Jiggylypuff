import time
from datetime import datetime
from typing import Literal

import discord
from discord import app_commands
from discord.ext import commands
from utils.db.market_value_db import pokemon_autocomplete

from utils.essentials.command_safe import run_command_safe
from utils.essentials.role_checks import auctioneer_only
from utils.group_commands_func.auction import *
from utils.logs.pretty_log import pretty_log
from utils.parser.number_parser import parse_compact_number

GROUP_NAME = "auction"  # change to "auction" when done testing
# 🎀────────────────────────────────────────────
#           🌸 Auction Cog Setup 🌸
# ─────────────────────────────────────────────


class AuctionGroupCommand(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # 🎀────────────────────────────────────────────
    #           🌸 Slash Command Group 🌸
    # 🎀────────────────────────────────────────────
    auction_group = app_commands.Group(
        name=GROUP_NAME, description="Commands related to auctions"
    )

    # 🎀────────────────────────────────────────────
    #          🌸 /auction start 🌸
    # 🎀────────────────────────────────────────────
    @auction_group.command(name="start", description="Starts an auction")
    @app_commands.describe(
        pokemon="Name of the Pokémon (e.g. Pikachu, Charizard)",
        duration="Auction duration (e.g. '5m', '3h')",
        autobuy="Autobuy price (e.g. '1k', '1.5m')",
        accepted_pokemon="Optional List of accepted Pokémon (comma-separated)",
    )
    @app_commands.autocomplete(pokemon=pokemon_autocomplete)
    async def auction_start(
        self,
        interaction: discord.Interaction,
        pokemon: str,
        duration: str,
        autobuy: str = None,
        accepted_pokemon: str = None,
    ):
        slash_cmd_name = "auction start"

        await run_command_safe(
            bot=self.bot,
            interaction=interaction,
            slash_cmd_name=slash_cmd_name,
            command_func=start_auction_func,
            pokemon=pokemon,
            duration=duration,
            autobuy=autobuy,
            accepted_pokemon=accepted_pokemon,
        )

    auction_start.extras = {"category": "Public"}

    # 🎀────────────────────────────────────────────
    #          🌸 /auction stop 🌸
    # 🎀────────────────────────────────────────────
    @auction_group.command(
        name="stop", description="Ends the active auction in this channel"
    )
    @auctioneer_only()
    async def auction_stop(self, interaction: discord.Interaction):
        slash_cmd_name = "auction end"

        await run_command_safe(
            bot=self.bot,
            interaction=interaction,
            slash_cmd_name=slash_cmd_name,
            command_func=stop_auction_func,
        )

    auction_stop.extras = {"category": "Staff"}

    # 🎀────────────────────────────────────────────
    #          🌸 /auction bid 🌸
    # 🎀────────────────────────────────────────────
    @auction_group.command(
        name="bid", description="Place a bid in the active auction in this channel"
    )
    @app_commands.describe(amount="Your bid amount (e.g. '1k', '1.5m')")
    async def auction_bid(self, interaction: discord.Interaction, amount: str):
        slash_cmd_name = "auction bid"

        await run_command_safe(
            bot=self.bot,
            interaction=interaction,
            slash_cmd_name=slash_cmd_name,
            command_func=bid_func,
            amount=amount,
        )

    auction_bid.extras = {"category": "Public"}

    # 🎀────────────────────────────────────────────
    #          🌸 /auction roll-back 🌸
    # 🎀────────────────────────────────────────────
    @auction_group.command(
        name="roll-back",
        description="Roll back a bid in the active auction in this channel",
    )
    @app_commands.describe(
        member="The member whose bid you want to roll back",
        amount="The amount to roll back (e.g. '1k', '1.5m')",
    )
    @auctioneer_only()
    async def auction_roll_back(
        self,
        interaction: discord.Interaction,
        member: discord.Member,
        amount: str,
    ):
        slash_cmd_name = "auction roll-back"

        await run_command_safe(
            bot=self.bot,
            interaction=interaction,
            slash_cmd_name=slash_cmd_name,
            command_func=roll_back_func,
            member=member,
            amount=amount,
        )

    auction_roll_back.extras = {"category": "Staff"}

    # 🎀────────────────────────────────────────────
    #          🌸 /auction update-ends-on 🌸
    # 🎀────────────────────────────────────────────
    @auction_group.command(
        name="update-ends-on",
        description="Update the end time of the active auction in this channel",
    )
    @app_commands.describe(
        action="Whether to add or subtract time from the auction end",
        duration="Duration to add or subtract (e.g. '5m', '2h')",
    )
    @auctioneer_only()
    async def auction_update_ends_on(
        self,
        interaction: discord.Interaction,
        action: Literal["add", "subtract"],
        duration: str,
    ):
        slash_cmd_name = "auction update-ends-on"

        await run_command_safe(
            bot=self.bot,
            interaction=interaction,
            slash_cmd_name=slash_cmd_name,
            command_func=update_ends_on_func,
            action=action,
            duration=duration,
        )

    auction_update_ends_on.extras = {"category": "Staff"}

    # 🎀────────────────────────────────────────────
    #          🌸 /auction banner 🌸
    # 🎀────────────────────────────────────────────
    @auction_group.command(
        name="banner", description="Sends the auction house banner image"
    )
    @auctioneer_only()
    async def auction_banner(self, interaction: discord.Interaction):
        slash_cmd_name = "auction banner"

        await run_command_safe(
            bot=self.bot,
            interaction=interaction,
            slash_cmd_name=slash_cmd_name,
            command_func=send_auction_house_banner_func,
        )

    auction_banner.extras = {"category": "Staff"}

    # 🎀────────────────────────────────────────────
    #          🌸 /auction info 🌸
    # 🎀────────────────────────────────────────────
    @auction_group.command(
        name="info",
        description="Displays information about the active auction in this channel",
    )
    async def auction_info(self, interaction: discord.Interaction):
        slash_cmd_name = "auction info"

        await run_command_safe(
            bot=self.bot,
            interaction=interaction,
            slash_cmd_name=slash_cmd_name,
            command_func=auction_info_func,
        )

    auction_info.extras = {"category": "Public"}


async def setup(bot: commands.Bot):
    await bot.add_cog(AuctionGroupCommand(bot))
