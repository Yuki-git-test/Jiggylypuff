import discord
from discord import app_commands
from discord.ext import commands

from utils.essentials.command_safe import run_command_safe
from utils.group_commands_func.accepted_list import *

GROUP_NAME = "accepted-list"


# 🎀────────────────────────────────────────────
#           🌸 Accepted List Cog Setup 🌸
# ─────────────────────────────────────────────
class Accepted_List_Group_Commands(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # 🎀────────────────────────────────────────────
    #           🌸 Slash Command Group 🌸
    # 🎀────────────────────────────────────────────
    accepted_list_group = app_commands.Group(
        name=GROUP_NAME, description="Commands related to accepted list for auctions"
    )

    # 🎀────────────────────────────────────────────
    #          🌸 /accepted-list view 🌸
    # 🎀────────────────────────────────────────────
    @accepted_list_group.command(
        name="view", description="View accepted list for the current auction"
    )
    async def accepted_list_view(
        self,
        interaction: discord.Interaction,
    ):
        slash_cmd_name = "market-value view"

        await run_command_safe(
            bot=self.bot,
            interaction=interaction,
            slash_cmd_name=slash_cmd_name,
            command_func=view_accepted_list_func,
        )

    accepted_list_view.extras = {"category": "Public"}

    # 🎀────────────────────────────────────────────
    #          🌸 /accepted-list update 🌸
    # 🎀────────────────────────────────────────────
    @accepted_list_group.command(
        name="update", description="Update accepted list for the current auction"
    )
    @app_commands.describe(
        new_accepted_list="New accepted Pokémon list (comma-separated)"
    )
    async def accepted_list_update(
        self,
        interaction: discord.Interaction,
        new_accepted_list: str,
    ):
        slash_cmd_name = "accepted-list update"

        await run_command_safe(
            bot=self.bot,
            interaction=interaction,
            slash_cmd_name=slash_cmd_name,
            command_func=update_accepted_list_func,
            new_accepted_list=new_accepted_list,
        )

    accepted_list_update.extras = {"category": "Staff"}

    # 🎀────────────────────────────────────────────
    #          🌸 /accepted-list clear 🌸
    # 🎀────────────────────────────────────────────
    @accepted_list_group.command(
        name="clear", description="Clear accepted list for the current auction"
    )
    async def accepted_list_clear(
        self,
        interaction: discord.Interaction,
    ):
        slash_cmd_name = "accepted-list clear"

        await run_command_safe(
            bot=self.bot,
            interaction=interaction,
            slash_cmd_name=slash_cmd_name,
            command_func=clear_accepted_list_func,
        )

    accepted_list_clear.extras = {"category": "Staff"}


async def setup(bot: commands.Bot):
    await bot.add_cog(Accepted_List_Group_Commands(bot))
