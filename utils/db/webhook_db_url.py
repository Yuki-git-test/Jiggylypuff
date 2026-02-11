import discord

from utils.logs.pretty_log import pretty_log

"""CREATE TABLE webhook_url (
    bot_id BIGINT NOT NULL,
    channel_id BIGINT NOT NULL,
    channel_name TEXT NOT NULL,
    url TEXT NOT NULL,
    PRIMARY KEY (bot_id, channel_id)
);"""


async def upsert_webhook_url(
    bot: discord.Client,
    channel: discord.TextChannel,
    url: str,
):
    bot_id = bot.user.id
    channel_id = channel.id
    channel_name = channel.name

    try:
        async with bot.pg_pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO webhook_url (bot_id, channel_id, channel_name, url)
                VALUES ($1, $2, $3, $4)
                ON CONFLICT (bot_id, channel_id) DO UPDATE
                SET channel_name = EXCLUDED.channel_name,
                    url = EXCLUDED.url
                """,
                bot_id,
                channel_id,
                channel_name,
                url,
            )
            pretty_log(
                message=f"✅ Upserted webhook URL for channel: {channel_name} (ID: {channel_id})",
                tag="db",
            )

            # Update cache
            from utils.cache.webhook_url_cache import upsert_webhook_url_into_cache

            upsert_webhook_url_into_cache(
                bot_id=bot_id,
                channel_id=channel_id,
                url=url,
            )
    except Exception as e:
        pretty_log(
            message=f"❌ Failed to upsert webhook URL for channel: {channel_name} (ID: {channel_id}): {e}",
            tag="error",
            include_trace=True,
        )


async def fetch_all_webhook_urls(bot: discord.Client):
    bot_id = bot.user.id
    try:
        async with bot.pg_pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT channel_id, channel_name, url
                FROM webhook_url
                WHERE bot_id = $1
                """,
                bot_id,
            )
            webhook_urls = []
            for row in rows:
                webhook_entry = {
                    "bot_id": bot_id,
                    "channel_id": row["channel_id"],
                    "channel_name": row["channel_name"],
                    "url": row["url"],
                }
                webhook_urls.append(webhook_entry)
            pretty_log(
                message=f"✅ Fetched {len(webhook_urls)} webhook URLs for bot ID: {bot_id}",
                tag="db",
            )
            return webhook_urls
    except Exception as e:
        pretty_log(
            message=f"❌ Failed to fetch webhook URLs for bot ID: {bot_id}: {e}",
            tag="error",
            include_trace=True,
        )
        return []


async def remove_webhook_url(
    bot: discord.Client,
    channel: discord.TextChannel,
):
    bot_id = bot.user.id
    channel_id = channel.id

    try:
        async with bot.pg_pool.acquire() as conn:
            result = await conn.execute(
                """
                DELETE FROM webhook_url
                WHERE bot_id = $1 AND channel_id = $2
                """,
                bot_id,
                channel_id,
            )
            if result.endswith("0"):
                pretty_log(
                    message=f"⚠️ No webhook URL found to delete for channel: {channel.name} (ID: {channel_id})",
                    tag="db",
                )
            else:
                pretty_log(
                    message=f"✅ Removed webhook URL for channel: {channel.name} (ID: {channel_id})",
                    tag="db",
                )
                # Update cache
                from utils.cache.webhook_url_cache import remove_webhook_url_from_cache

                remove_webhook_url_from_cache(
                    bot_id=bot_id,
                    channel_id=channel_id,
                )
    except Exception as e:
        pretty_log(
            message=f"❌ Failed to remove webhook URL for channel: {channel.name} (ID: {channel_id}): {e}",
            tag="error",
            include_trace=True,
        )
