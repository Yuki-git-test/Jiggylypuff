import discord

from constants.aesthetic import Images


async def send_auction_house_banner_func(bot, interaction: discord.Interaction):
    """Sends the auction house banner image in the current channel."""
    await interaction.response.send_message(content=Images.auction_house_open)
