import discord

from utils.db.auction_db import update_broadcast_msg_id
from utils.logs.pretty_log import pretty_log

TEST_BROADCAST_CHANNEL_ID = 1469896953709068550
BROADCAST_CHANNEL_ID = TEST_BROADCAST_CHANNEL_ID


async def broadcast_auction(
    bot: discord.Client,
    guild: discord.Guild,
    embed: discord.Embed,
):
    broadcast_channel = guild.get_channel(BROADCAST_CHANNEL_ID)
    # Send to broadcast channel if it exists
    if broadcast_channel:
        auction_msg = await broadcast_channel.send(embed=embed)
        await update_broadcast_msg_id(bot, auction_msg.id, auction_msg.channel.id)
        # publish message
        try:
            await auction_msg.publish()
        except Exception as e:
            pretty_log(
                "error",
                f"Failed to publish auction message in broadcast channel: {e}",
                include_trace=True,
            )
