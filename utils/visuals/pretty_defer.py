import discord

from constants.aesthetic import *
from utils.logs.pretty_log import pretty_log

LOADING_EMOJI = Emojis.loading
CHECK_EMOJI = Emojis.check
ERROR_EMOJI = Emojis.error


async def pretty_defer(
    interaction: discord.Interaction,
    view: discord.ui.View | None = None,
    content: str = "Please wait while Jigglypuff thinks...",
    embed: discord.Embed | None = None,
    ephemeral: bool = True,
):
    """
    Fully safe Jigglypuff loader for interactions.
    - Don't forget to await
    - Always prefers editing the original response.
    - Sends a public fallback message if editing is not possible.
    - Success can override ephemeral by deleting it and sending a public message.
    """

    class PrettyDeferHandle:
        def __init__(
            self,
            interaction: discord.Interaction,
            message: discord.Message | None,
            ephemeral: bool,
        ):
            self.interaction = interaction
            self.message = message
            self.message_id = message.id if message else None
            self.stopped = False
            self._emoji_added = False
            self.ephemeral = ephemeral
            self.error_emoji = "❌"  # Replaceable error emoji

        async def _resolve_message(self) -> discord.Message | None:
            """Try to ensure we always have the original response if possible."""
            if self.message:
                return self.message
            try:
                self.message = await self.interaction.original_response()
                return self.message
            except Exception:
                return None

        async def edit(
            self, content=None, embed=None, view=None, with_emoji: bool = True
        ):
            if self.stopped:
                return
            msg = await self._resolve_message()
            if not msg:
                try:
                    msg = await self.interaction.followup.send(
                        content=(
                            f"{LOADING_EMOJI} {content}"
                            if content and with_emoji
                            else content
                        ),
                        embed=embed,
                        view=view,
                        ephemeral=self.ephemeral,
                    )
                    self.message = msg
                    self.message_id = msg.id
                    return
                except Exception as e:
                    pretty_log(
                        "❌ ERROR",
                        f"[pretty_defer.edit] followup failed: {e}",
                    )
                    return

            if content and with_emoji:
                content = f"{LOADING_EMOJI} {content}"

            kwargs = {
                k: v
                for k, v in {"content": content, "embed": embed, "view": view}.items()
                if v is not None
            }
            try:
                await msg.edit(**kwargs)
            except Exception as e:
                pretty_log(
                    "❌ ERROR",
                    f"[pretty_defer.edit] {e}",
                )

        async def stop(self, content=None, embed=None, view=None):
            if self.stopped:
                return
            self.stopped = True
            msg = await self._resolve_message()
            if not msg:
                return
            kwargs = {
                k: v
                for k, v in {"content": content, "embed": embed, "view": view}.items()
                if v is not None
            }
            if kwargs:
                try:
                    await msg.edit(**kwargs)
                except Exception as e:
                    pretty_log(
                        "❌ ERROR",
                        f"[pretty_defer.stop] {e}",
                    )

        async def success(
            self,
            content: str | None = "Done!",
            embed: discord.Embed | None = None,
            view: discord.ui.View | None = None,
            ephemeral: bool | None = None,  # override ephemeral flag
            override_public: bool = False,  # force public even if initial was ephemeral
            delete: bool = False,  # if True, deletes the loader message instead of editing
            add_check_emoji: bool = True,  # whether to add a check emoji on success
        ):
            """Mark interaction as completed."""
            if self.stopped:
                return
            self.stopped = True
            msg = await self._resolve_message()

            if delete and msg:
                try:
                    await msg.delete()
                except Exception as e:
                    pretty_log(
                        "❌ ERROR",
                        f"[pretty_defer.success] delete failed: {e}",
                    )
                return

            final_ephemeral = ephemeral if ephemeral is not None else self.ephemeral

            base_content = content or ""
            if add_check_emoji and base_content:
                content_with_emoji = f"{CHECK_EMOJI} {base_content}"
            else:
                content_with_emoji = base_content

            try:
                if final_ephemeral and not override_public:
                    if msg:
                        try:
                            await msg.edit(
                                content=content_with_emoji, embed=embed, view=view
                            )
                            return
                        except Exception:
                            pass
                    await self.interaction.followup.send(
                        content=content_with_emoji,
                        embed=embed,
                        view=view,
                        ephemeral=True,
                    )
                else:
                    if override_public and self.ephemeral:
                        if msg:
                            try:
                                await msg.delete()
                            except Exception:
                                pass
                    if msg:
                        try:
                            await msg.edit(
                                content=content_with_emoji, embed=embed, view=view
                            )
                            return
                        except Exception:
                            pass
                    if getattr(self.interaction, "channel", None):
                        await self.interaction.channel.send(
                            content=content_with_emoji, embed=embed, view=view
                        )

            except Exception as e:
                pretty_log(
                    "❌ ERROR",
                    f"[pretty_defer.success] {e}",
                )

        async def error(
            self,
            content: str = "An error occurred.",
            embed: discord.Embed | None = None,
        ):
            """Immediately mark loader as error, always ephemeral, then return."""
            if self.stopped:
                return
            self.stopped = True
            msg = await self._resolve_message()
            content_with_emoji = f"{ERROR_EMOJI} {content}"

            try:
                if msg:
                    if self.ephemeral:
                        await msg.edit(content=content_with_emoji, embed=embed)
                    else:
                        # public initial → send ephemeral followup then delete initial
                        await self.interaction.followup.send(
                            content=content_with_emoji, embed=embed, ephemeral=True
                        )
                        try:
                            await msg.delete()
                        except Exception:
                            pass
                else:
                    await self.interaction.followup.send(
                        content=content_with_emoji, embed=embed, ephemeral=True
                    )
            except Exception as e:
                pretty_log(
                    "❌ ERROR",
                    f"[pretty_defer.error] {e}",
                )
            return  # always return immediately

    # ----------------- Send initial loader -----------------
    msg: discord.Message | None = None
    msg_content = f"{LOADING_EMOJI} {content}"

    try:
        if (
            getattr(interaction, "response", None)
            and not interaction.response.is_done()
        ):
            await interaction.response.send_message(
                content=msg_content, embed=embed, view=view, ephemeral=ephemeral
            )
            try:
                msg = await interaction.original_response()
            except Exception:
                pass
        else:
            msg = await interaction.followup.send(
                content=msg_content, embed=embed, view=view, ephemeral=ephemeral
            )
    except Exception:
        pass

    handle = PrettyDeferHandle(interaction, msg, ephemeral=ephemeral)
    if view:
        setattr(view, "defer_handle", handle)

    return handle


# ╭───────────────────────────────╮
#   🌊 Pretty Error Helper
# ╰───────────────────────────────╯
async def pretty_error(
    interaction: discord.Interaction,
    content: str = "An error occurred.",
    embed: discord.Embed | None = None,
):
    """
    Standalone ephemeral error sender for Jigglypuff.
    - Always ephemeral.
    - Uses Jigglypuff's error emoji.
    - Returns early (no loader needed).
    """

    content_with_emoji = f"{ERROR_EMOJI} {content}"

    try:
        if (
            getattr(interaction, "response", None)
            and not interaction.response.is_done()
        ):
            await interaction.response.send_message(
                content=content_with_emoji,
                embed=embed,
                ephemeral=True,
            )
        else:
            await interaction.followup.send(
                content=content_with_emoji,
                embed=embed,
                ephemeral=True,
            )
    except Exception as e:
        pretty_log(
            "❌ ERROR",
            f"[pretty_error] Failed to send error message: {e}",
        )
