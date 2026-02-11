# cogs/essentials/role_checks.py
import discord
from discord import app_commands

from constants.grand_line_auction_constants import GRAND_LINE_AUCTION_ROLES, KHY_USER_ID


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
        # Allow khy (user id: 952071312124313611)
        if getattr(interaction.user, "id", None) == KHY_USER_ID:
            return True
        if not has_role(interaction.user.roles, GRAND_LINE_AUCTION_ROLES.auctioneer):
            raise AuctioneerCheckFailure(ERROR_MESSAGES["auctioneer"])
        return True

    return app_commands.check(predicate)


# Check if user is staff member
def is_staff_member(member: discord.Member) -> bool:
    """
    Checks if a member has any staff roles.
    """
    # Allow khy (user id: 952071312124313611)
    if getattr(member, "id", None) == KHY_USER_ID:
        return True
    staff_role_ids = [
        GRAND_LINE_AUCTION_ROLES.auctioneer,
        GRAND_LINE_AUCTION_ROLES.moderator,
    ]
    if any(role.id in staff_role_ids for role in member.roles):
        return True
    return False
