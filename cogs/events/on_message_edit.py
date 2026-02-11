import re

import discord
from discord.ext import commands

from constants.grand_line_auction_constants import (
    CC_SERVER_ID,
    GLA_SERVER_ID,
    POKEMEOW_APPLICATION_ID,
)
from utils.listener_func.price_data_listener import price_data_listener
from utils.logs.pretty_log import pretty_log

# ️────────────────────────────────────────────
#        ⚔️ Message Triggers
# ️────────────────────────────────────────────
triggers = {
    "price_data_listener": "Market Data & Trends",
}


# 🍭──────────────────────────────
#   🎀 Event: On Message Edit
# 🍭──────────────────────────────
class OnMessageEditCog(commands.Cog):
    """Cog to handle message edit events."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_message_edit(self, before: discord.Message, after: discord.Message):

        # Ignore edits made by bots except PokéMeow
        if after.author.bot and after.author.id != POKEMEOW_APPLICATION_ID:
            return

        content = after.content if after.content else ""
        first_embed = after.embeds[0] if after.embeds else None
        first_embed_author_text = (
            first_embed.author.name if first_embed and first_embed.author else ""
        )
        first_embed_description = first_embed.description if first_embed else ""
        first_embed_footer_text = (
            first_embed.footer.text if first_embed and first_embed.footer else ""
        )
        first_embed_title = first_embed.title if first_embed else ""

        # ————————————————————————————————
        # 🩵 GLA Edit Listener
        # ————————————————————————————————
        # Only log edits in GLA or CC server
        if not after.guild or (
            after.guild.id != GLA_SERVER_ID and after.guild.id != CC_SERVER_ID
        ):
            return

        # ————————————————————————————————
        # 🩵 GLA Price Data Listener
        # ————————————————————————————————
        if first_embed:
            if (
                first_embed_title
                and triggers["price_data_listener"] in first_embed_title
            ):
                pretty_log(
                    "info",
                    f"Detected edit with embed title containing '{triggers['price_data_listener']}'. Triggering price data listener.",
                )
                await price_data_listener(self.bot, after)


async def setup(bot: commands.Bot):
    await bot.add_cog(OnMessageEditCog(bot))
