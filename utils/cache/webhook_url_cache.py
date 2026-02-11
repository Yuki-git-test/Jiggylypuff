import discord

from utils.cache.cache_list import webhook_url_cache
from utils.db.webhook_db_url import fetch_all_webhook_urls
from utils.logs.pretty_log import pretty_log


async def load_webhook_url_cache(bot: discord.Client):
    webhook_url_cache.clear()
    try:
        webhook_urls = await fetch_all_webhook_urls(bot)
        if not webhook_urls:
            """pretty_log(
                message="⚠️ No webhook URLs found to load into cache.",
                tag="cache",
            )"""
            return

        for entry in webhook_urls:
            key = (entry["bot_id"], entry["channel_id"])
            webhook_url_cache[key] = entry["url"]

        """pretty_log(
            message=f"✅ Loaded {len(webhook_url_cache)} webhook URLs into cache.",
            tag="cache",
        )

        if len(webhook_url_cache) == 0:
            pretty_log(
                message="⚠️ Webhook URL cache is empty after loading.",
                tag="cache",
            )"""
        return webhook_url_cache

    except Exception as e:
        pretty_log(
            message=f"❌ Error loading webhook URL cache: {e}",
            tag="cache",
        )
        raise e


def upsert_webhook_url_into_cache(
    bot_id: int,
    channel_id: int,
    url: str,
):
    key = (bot_id, channel_id)
    webhook_url_cache[key] = url
    pretty_log(
        message=f"✅ Upserted webhook URL into cache for bot ID: {bot_id}, channel ID: {channel_id}",
        tag="cache",
    )


def remove_webhook_url_from_cache(
    bot_id: int,
    channel_id: int,
):
    key = (bot_id, channel_id)
    if key in webhook_url_cache:
        del webhook_url_cache[key]
        pretty_log(
            message=f"✅ Removed webhook URL from cache for bot ID: {bot_id}, channel ID: {channel_id}",
            tag="cache",
        )


def fetch_webhook_url_from_cache(
    bot_id: int,
    channel_id: int,
):
    key = (bot_id, channel_id)
    return webhook_url_cache.get(key)
