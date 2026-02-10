# utils/loggers/smart_debug.py
import inspect
from datetime import datetime
import discord

# -----------------------------
# 🔹 Global Debug Toggles
# -----------------------------
DEBUG_TOGGLES: dict[str, bool] = {}


def enable_debug(func_path: str):
    DEBUG_TOGGLES[func_path] = True


def disable_debug(func_path: str):
    DEBUG_TOGGLES[func_path] = False


def debug_enabled(func_path: str) -> bool:
    return DEBUG_TOGGLES.get(func_path, False)


# -----------------------------
# 🔹 Core debug_log
# -----------------------------
def debug_log(
    message: str, highlight: bool = False, disabled: bool = False, force: bool = False
):
    if disabled:
        return

    stack = inspect.stack()
    caller_frame = stack[1]
    func_name = caller_frame.function
    module_name = caller_frame.frame.f_globals.get("__name__", "__main__")
    key = f"{module_name}.{func_name}"

    if not debug_enabled(key) and not force:
        return

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_line = f"[{timestamp}] [🧪 {func_name}] {message}"

    # 🌸 pastel pink + underline for highlights
    COLOR_PASTEL_PINK = "\033[38;2;255;182;193m\033[4m"
    COLOR_RESET = "\033[0m"

    if highlight:
        log_line = f"{COLOR_PASTEL_PINK}{log_line}{COLOR_RESET}"

    print(log_line)


# -----------------------------
# 🔹 Sub-function: Debug Message Content
# -----------------------------
def debug_message_content(message: discord.Message, force: bool = True):
    """
    Dumps the raw message content and embeds for inspection.
    If force=True, prints regardless of debug toggles.
    """
    debug_log("Raw message content dump:", force=force)
    debug_log(f"Message ID: {message.id}", force=force)
    debug_log(f"Author: {message.author} ({message.author.id})", force=force)
    debug_log(f"Content: {message.content!r}", force=force)
    debug_log(f"Embeds count: {len(message.embeds)}", force=force)

    for idx, embed in enumerate(message.embeds, start=1):
        debug_log(
            f"Embed {idx}: title={embed.title!r}, description={embed.description!r}",
            force=force,
        )
        for f_idx, field in enumerate(embed.fields, start=1):
            debug_log(
                f"  Field {f_idx}: name={field.name!r}, value={field.value!r}, inline={field.inline}",
                force=force,
            )
