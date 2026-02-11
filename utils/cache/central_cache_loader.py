import discord

from utils.db.market_value_db import load_market_cache_from_db
from utils.logs.pretty_log import pretty_log

from .auction_cache import load_auction_cache
from .webhook_url_cache import load_webhook_url_cache


async def load_all_cache(bot: discord.Client):
    """
    Loads all caches used by the bot.
    Currently loads:
    - Market Alert Cache
    """
    try:

        # Load Auction Cache
        await load_auction_cache(bot)

        # Load Market Value Cache from database
        await load_market_cache_from_db(bot)

        # Load Webhook URL Cache
        await load_webhook_url_cache(bot)

    except Exception as e:
        pretty_log(
            message=f"❌ Error loading caches: {e}",
            tag="cache",
        )
        return
    """pretty_log(
        message="✅ All caches loaded successfully.",
        tag="cache",
    )"""
