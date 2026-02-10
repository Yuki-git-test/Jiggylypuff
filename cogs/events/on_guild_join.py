from datetime import datetime

import discord
from discord.ext import commands

from constants.grand_line_auction_constants import (
    GLA_SERVER_ID,
    GRAND_LINE_AUCTION_TEXT_CHANNELS,
    YUKI_USER_ID,
)

LOG_CHANNEL_ID = GRAND_LINE_AUCTION_TEXT_CHANNELS.server_logs

ALLOWED_GUILD_IDS = [GLA_SERVER_ID, 1220718310455250996, 1311620784720183316]

from utils.logs.pretty_log import pretty_log


# 🍭──────────────────────────────
#   🎀 Cog: On Guild Join
# 🍭──────────────────────────────
class OnGuildJoinCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_guild_join(self, guild: discord.Guild):
        bot_owner = self.bot.get_user(YUKI_USER_ID)
        main_guild: discord.Guild = self.bot.get_guild(GLA_SERVER_ID)
        if guild.id not in ALLOWED_GUILD_IDS:
            # Log the event to server log channel
            log_channel = main_guild.get_channel(LOG_CHANNEL_ID)
            log_embed = discord.Embed(
                title="❌ Unrecognized Guild Joined",
                description=(
                    f"The bot has joined an unrecognized guild:\n"
                    f"**Guild Name:** {guild.name}\n"
                    f"**Guild ID:** {guild.id}\n"
                    f"**Member Count:** {guild.member_count}\n"
                    f"**Owner:** {guild.owner} ({guild.owner_id})"
                ),
                color=discord.Color.red(),
                timestamp=datetime.now(),
            )
            footer_text = "I will be leaving this guild shortly."
            log_embed.set_footer(text=footer_text)
            log_embed.set_thumbnail(url=guild.icon.url if guild.icon else "")
            if log_channel:
                await log_channel.send(embed=log_embed)

            # Notify guild owner
            guild_owner = guild.owner
            if guild_owner:
                try:
                    dm_embed = discord.Embed(
                        title="❌ Unrecognized Guild",
                        description=(
                            f"Hello! I am Jigglypuff, a bot primarily designed for the {main_guild.name} server. "
                            f"It seems that I have joined your guild '{guild.name}', but I am not intended to operate outside of my main server.\n\n"
                            f"As such, I will be leaving your guild shortly. If you believe this is a mistake or would like to discuss further, please contact my owner: Yuki - {bot_owner.mention}."
                        ),
                        color=discord.Color.red(),
                    )
                    await guild_owner.send(embed=dm_embed)
                except Exception as e:
                    pretty_log(
                        message=f"❌ Failed to DM guild owner {guild_owner} ({guild_owner.id}): {e}",
                        tag="error",
                    )
            # Leave the guild
            await guild.leave()
            pretty_log(
                message=f"❌ Left unrecognized guild: {guild.name} (ID: {guild.id})",
                tag="info",
            )
        else:
            # Log the successful join to server log channel
            log_channel = main_guild.get_channel(LOG_CHANNEL_ID)
            log_embed = discord.Embed(
                title="✅ Joined Authorized Guild",
                description=(
                    f"The bot has joined an authorized guild:\n"
                    f"**Guild Name:** {guild.name}\n"
                    f"**Guild ID:** {guild.id}\n"
                    f"**Member Count:** {guild.member_count}\n"
                    f"**Owner:** {guild.owner} ({guild.owner_id})"
                ),
                color=discord.Color.green(),
                timestamp=datetime.now(),
            )
            log_embed.set_thumbnail(url=guild.icon.url if guild.icon else "")
            if log_channel:
                await log_channel.send(embed=log_embed)
            pretty_log(
                message=f"✅ Joined recognized guild: {guild.name} (ID: {guild.id})",
                tag="info",
            )


async def setup(bot):
    await bot.add_cog(OnGuildJoinCog(bot))
