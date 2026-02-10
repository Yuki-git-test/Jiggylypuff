# ❀───────────────────────────────❀
#       💖  Imports  💖
# ❀───────────────────────────────❀
import asyncio
import glob
import logging
import os
import random
from datetime import datetime
from zoneinfo import ZoneInfo

import discord
from discord import app_commands
from discord.ext import commands, tasks
from dotenv import load_dotenv

from utils.cache.central_cache_loader import load_all_cache
from utils.db.get_pg_pool import *
from utils.logs.pretty_log import pretty_log, set_jiggly_bot
#
# ❀───────────────────────────────❀
#       💖  Suppress Logs  💖
# ❀───────────────────────────────❀
logging.basicConfig(level=logging.CRITICAL)
for logger_name in [
    "discord",
    "discord.gateway",
    "discord.http",
    "discord.voice_client",
    "asyncio",
]:
    logging.getLogger(logger_name).setLevel(logging.CRITICAL)
logging.getLogger("discord.client").setLevel(logging.CRITICAL)

# ❀───────────────────────────────❀
#       💖  Bot Factory  💖
# ❀───────────────────────────────❀
intents = discord.Intents.default()
intents.messages = True
intents.guilds = True
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)
set_jiggly_bot(bot)

# ❀───────────────────────────────❀
#   💖  App Command Error Handler 💖
# ❀───────────────────────────────❀


@bot.tree.error
async def on_app_command_error(interaction, error):
    from utils.essentials.role_checks import AuctioneerCheckFailure

    if isinstance(error, AuctioneerCheckFailure):
        await interaction.response.send_message(str(error), ephemeral=True)
    elif isinstance(error, app_commands.CheckFailure):
        await interaction.response.send_message(
            "You don't have permission to use this command.", ephemeral=True
        )
    else:
        await interaction.response.send_message("An error occurred.", ephemeral=True)
    pretty_log(
        tag="info",
        message=f"App command error: {error}",
        include_trace=True,
    )


# ❀───────────────────────────────❀
#       💖  Task Refresh Every 5 Minutes 💖
# ❀───────────────────────────────❀
@tasks.loop(minutes=5)
async def refresh_all_caches():

    # Removed first-run skip logic so cache loads immediately
    await load_all_cache(bot)


# ❀───────────────────────────────❀
#   💖  Prefix Command Error Handler 💖
# ❀───────────────────────────────❀
@bot.event
async def on_command_error(ctx, error):
    # Ignore prefix command not found
    if isinstance(error, commands.CommandNotFound):
        return

    # Handle other prefix errors
    await ctx.send("❌ Something went wrong.")
    pretty_log(
        tag="error",
        message=f"Prefix command error: {error}",
        include_trace=True,
    )


# ❀───────────────────────────────❀
#       💖  Event Hooks 💖
# ❀───────────────────────────────❀
# ❀ On Ready ❀
@bot.event
async def on_ready():
    pretty_log("ready", f"Jigglypuff bot awake as {bot.user}")

    # ❀ Sync slash commands ❀
    await bot.tree.sync()

    # ❀ Log how many slash commands were synced ❀
    total_commands = len(bot.tree.get_commands())
    pretty_log("ready", f"Synced {total_commands} slash commands.")

    # Start the cache refresh task if it's not already running
    if not refresh_all_caches.is_running():
        refresh_all_caches.start()
        pretty_log(message="✅ Started cache refresh task", tag="ready")


# ❀───────────────────────────────❀
#       💖  Setup Hook 💖
# ❀───────────────────────────────❀
@bot.event
async def setup_hook():
    # ❀ PostgreSQL connection ❀
    try:
        bot.pg_pool = await get_pg_pool()
    except Exception as e:
        pretty_log("critical", f"Postgres connection failed: {e}", include_trace=True)

    # ❀ Load all cogs, skip __init__.py ❀
    for cog_path in glob.glob("cogs/**/*.py", recursive=True):
        if os.path.basename(cog_path) == "__init__.py":
            continue
        relative_path = os.path.relpath(cog_path, "cogs")
        module_name = relative_path[:-3].replace(os.sep, ".")
        cog_name = f"cogs.{module_name}"
        try:
            await bot.load_extension(cog_name)
        except Exception as e:
            pretty_log("error", f"Failed to load {cog_name}: {e}", include_trace=True)


# ❀───────────────────────────────❀
#       💖  Main Async Runner 💖
# ❀───────────────────────────────❀
async def main():
    load_dotenv()
    pretty_log("ready", "Jigglypuff Bot is starting...")

    retry_delay = 5
    while True:
        try:
            await bot.start(os.getenv("DISCORD_TOKEN"))
        except KeyboardInterrupt:
            pretty_log("ready", "Shutting down Jigglypuff Bot...")
            break
        except Exception as e:
            pretty_log("error", f"Bot crashed: {e}", include_trace=True)
            pretty_log(
                "ready", f"Restarting Jigglypuff Bot in {retry_delay} seconds..."
            )
            await asyncio.sleep(retry_delay)
            retry_delay = min(retry_delay * 2, 60)


# ❀───────────────────────────────❀
#       💖  Entry Point 💖
# ❀───────────────────────────────❀
if __name__ == "__main__":
    asyncio.run(main())
