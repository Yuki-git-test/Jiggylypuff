# cogs/essentials/role_checks.py
import discord
from discord import app_commands

from constants.grand_line_auction_constants import GRAND_LINE_AUCTION_ROLES


# 🌸──────────────────────────────────────────────────────
# ✨ Custom Exceptions (Sparkles & Cute!) ✨
# ───────────────────────────────────────────────────────
class AuctioneerCheckFailure(app_commands.CheckFailure):
    pass


# 🌸──────────────────────────────────────────────────────
# 🐾💫 Cute Error Messages by Server — Cottagecore Style 💫🌿
# ───────────────────────────────────────────────────────
ERROR_MESSAGES = {
    "auctioneer": "Only Auctioneers can use this command! If you think this is a mistake, please contact a Staff member.",
}


# 🌸──────────────────────────────────────────────────────
# 🔹 Helper function
# ───────────────────────────────────────────────────────
def has_role(user_roles, role_id):
    """Check if user has a role ID"""
    return role_id in [role.id for role in user_roles]


# 🌸──────────────────────────────────────────────────────
# 🔹 Slash command decorators
# ───────────────────────────────────────────────────────
def auctioneer_only():
    async def predicate(interaction: discord.Interaction):
        if not has_role(interaction.user.roles, GRAND_LINE_AUCTION_ROLES.auctioneer):
            raise AuctioneerCheckFailure(ERROR_MESSAGES["auctioneer"])
        return True

    return app_commands.check(predicate)
