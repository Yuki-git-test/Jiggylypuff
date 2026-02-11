import discord

from constants.grand_line_auction_constants import GLA_SERVER_ID
from utils.cache.auction_cache import get_auction_cache
from utils.group_commands_func.auction.start import make_auction_embed
from utils.logs.pretty_log import pretty_log
from utils.visuals.pretty_defer import pretty_defer

from .start import is_being_processed


async def auction_info_func(bot: discord.Client, interaction: discord.Interaction):
    channel = interaction.channel
    channel_id = channel.id
    loader = await pretty_defer(
        interaction=interaction, content="Fetching Auction Info...", ephemeral=False
    )
    auction = get_auction_cache(channel_id)
    if not auction:
        await loader.error(content="This channel does not have an active auction.")
        return

    guild = bot.get_guild(GLA_SERVER_ID)

    # Check if auction is already being processed
    processing_message = is_being_processed(channel_id)
    if processing_message:
        await loader.error(content=processing_message)
        return

    # Get auction details
    host_id = auction["host_id"]
    is_bulk = auction.get("is_bulk", False)
    host = guild.get_member(host_id)
    if not host:
        # Fetch discord use
        host = await guild.fetch_member(host_id)
    highest_bidder_id = auction["highest_bidder_id"]
    highest_bidder = None
    if highest_bidder_id:
        highest_bidder = guild.get_member(highest_bidder_id)
        if not highest_bidder:
            highest_bidder = await guild.fetch_member(highest_bidder_id)
            if not highest_bidder:
                highest_bidder = None

    # Send auction ended message
    try:
        embed, content = make_auction_embed(
            bot=bot,
            user=host,
            pokemon=auction["pokemon"],
            unix_end=auction["ends_on"],
            autobuy=auction["autobuy"],
            accepted_pokemon=auction["accepted_list"],
            gif_url=auction["image_link"],
            highest_offer=auction["highest_offer"] if highest_bidder else 0,
            highest_bidder=highest_bidder if highest_bidder else None,
            last_bidder_mention=auction.get("last_bidder_mention", None),
            context="info",
            min_increment=auction["minimum_increment"],
            is_bulk=is_bulk,
        )
        await loader.success(content="", embed=embed, add_check_emoji=False)
        pretty_log(
            tag="auction",
            message=f"Sent auction info for channel  {interaction.channel.name}",
            bot=bot,
        )
    except Exception as e:
        pretty_log(
            tag="error",
            message=f"Error sending auction info for channel ID {channel_id}: {e}",
            include_trace=True,
            bot=bot,
        )
        await loader.error(content="An error occurred while fetching auction info.")
