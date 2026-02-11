import discord
from discord.ext import commands

from constants.grand_line_auction_constants import (
    CC_SERVER_ID,
    GLA_SERVER_ID,
    MH_APP_ID,
    POKEMEOW_APPLICATION_ID,
)
from utils.listener_func.dex_listener import dex_listener

# ————————————————————————————————
# 🩵 Import Listener Functions
# ————————————————————————————————
from utils.listener_func.market_view_listener import market_view_listener
from utils.listener_func.mh_lookup_listener import lookup_listener
from utils.logs.pretty_log import pretty_log


def embed_has_field_name(embed, name_to_match: str) -> bool:
    """
    Returns True if any field name in the embed matches the given string.
    Returns False immediately if the embed has no fields.
    """
    if not hasattr(embed, "fields") or not embed.fields:
        return False
    for field in embed.fields:
        if field.name == name_to_match:
            return True
    return False


# 🐾────────────────────────────────────────────
#        🌸 Message Create Listener Cog
# 🐾────────────────────────────────────────────
class MessageCreateListener(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # 🦋────────────────────────────────────────────
    #           👂 Message Listener Event
    # 🦋────────────────────────────────────────────
    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):

        # ————————————————————————————————
        # 🏰 Guild Check — Route by server
        # ————————————————————————————————
        guild = message.guild
        if not guild:
            return  # Skip DMs
        if guild.id != GLA_SERVER_ID and guild.id != CC_SERVER_ID:
            return  # Only process messages from VN Allstars server

        try:
            # ————————————————————————————————
            # 🩵 MH Lookup Listener
            # ————————————————————————————————
            if message.author.bot and message.author.id == MH_APP_ID:
                if message.embeds and message.embeds[0]:
                    if embed_has_field_name(message.embeds[0], "Lowest Market"):
                        pretty_log(
                            "info",
                            f"Detected MH lookup embed with 'Lowest Market' field. Triggering MH lookup listener.",
                        )
                        await lookup_listener(self.bot, message)

            # ————————————————————————————————
            # 🏰 Ignore non-PokéMeow bot messages
            # ————————————————————————————————
            # 🚫 Ignore all bots except PokéMeow to prevent loops
            if (
                message.author.bot
                and message.author.id != POKEMEOW_APPLICATION_ID
                and not message.webhook_id
            ):
                return

            content = message.content
            first_embed = message.embeds[0] if message.embeds else None
            first_embed_author = (
                first_embed.author.name if first_embed and first_embed.author else ""
            )
            first_embed_description = (
                first_embed.description
                if first_embed and first_embed.description
                else ""
            )
            first_embed_footer = (
                first_embed.footer.text if first_embed and first_embed.footer else ""
            )
            first_embed_title = (
                first_embed.title if first_embed and first_embed.title else ""
            )

            # ————————————————————————————————
            # 🩵 GLA MARKET VIEW LISTENER
            # ————————————————————————————————
            if (
                first_embed
                and "PokeMeow Global Market" in first_embed_author
                and not "Recent" in first_embed_author
                and not "Rarity" in first_embed_author
            ):
                pretty_log(
                    tag="info",
                    message=f"Processing market view message with embed author: {first_embed_author}",
                )
                await market_view_listener(self.bot, message)

            # ————————————————————————————————
            # 🩵 DEX LISTENER
            # ————————————————————————————————
            if first_embed:
                if embed_has_field_name(first_embed, "Dex Number"):
                    pretty_log(
                        "info",
                        f"Detected dex command embed with 'Dex Number' field. Triggering dex listener.",
                    )
                    await dex_listener(self.bot, message)

        except Exception as e:
            # 🛑────────────────────────────────────────────
            #        Unhandled on_message Error Handler
            # 🛑────────────────────────────────────────────
            pretty_log(
                "critical",
                f"Unhandled exception in on_message: {e}",
                label="MESSAGE",
                bot=self.bot,
                include_trace=True,
            )


# 🌈────────────────────────────────────────────
#        🛠️ Setup function to add cog to bot
# 🌈────────────────────────────────────────────
async def setup(bot: commands.Bot):
    await bot.add_cog(MessageCreateListener(bot))
