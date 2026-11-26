import os
import re
from types import SimpleNamespace

import discord

# Theme: "black" (default) makes every card a clean black card. Set the variable EMBED_THEME=color to get status colours back.
THEME = os.getenv("EMBED_THEME", "black").strip().lower()
BLACK = discord.Color.from_rgb(1, 1, 1)  # not 0,0,0: Discord treats pure black as "no colour" and draws a grey bar
if THEME == "color":
    COLOR = discord.Color.from_rgb(43, 45, 49)
    ACCENT = discord.Color.from_rgb(88, 101, 242)
    SUCCESS = discord.Color.from_rgb(46, 204, 113)
    WARN = discord.Color.from_rgb(250, 166, 26)
    DANGER = discord.Color.from_rgb(237, 66, 69)
    INFO = discord.Color.from_rgb(79, 157, 255)
    CARD_ACCENT_HEX = "5865F2"
else:
    COLOR = ACCENT = SUCCESS = WARN = DANGER = INFO = BLACK
    CARD_ACCENT_HEX = "141414"  # the welcome banner image: near-black gradient

# ------------------------------------------------------------ Custom emojis ----
# Black-and-white emoji pack. Each entry shows a monochrome fallback until you
# upload its image (emoji pack: xzx_<name>.png) to your server and paste the ID
# into _EMOJI_IDS below. 0 means "use the fallback". Static: <:name:ID>.
# Usage in cogs: from common import E  ->  f"{E.check} Done", f"{E.lock} Locked".
_EMOJI_IDS = {
    "check": 0, "cross": 0, "warn": 0, "info": 0, "alert": 0, "star": 0, "ticket": 0,
    "crown": 0, "lock": 0, "unlock": 0, "key": 0, "shop": 0, "cart": 0, "gift": 0,
    "wave": 0, "bot": 0, "pin": 0, "tack": 0, "clock": 0, "hourglass": 0, "chart": 0,
    "tool": 0, "gear": 0, "trash": 0, "link": 0, "coin": 0, "shield": 0, "user": 0,
    "users": 0, "roles": 0, "chat": 0, "note": 0, "edit": 0, "package": 0, "receipt": 0,
    "screen": 0, "bell": 0, "zap": 0, "rocket": 0, "scroll": 0, "clip": 0, "calendar": 0,
    "gem": 0, "globe": 0, "test": 0, "ban": 0, "game": 0, "announce": 0, "money": 0,
    "plus": 0, "minus": 0, "image": 0, "film": 0, "mail": 0, "book": 0, "file": 0,
    "folder": 0, "home": 0, "idea": 0, "refresh": 0, "sound": 0, "mute": 0, "trophy": 0,
    "search": 0, "fire": 0, "flag": 0, "clean": 0, "door": 0, "clipboard": 0, "id": 0,
    "hashtag": 0, "scale": 0, "seed": 0, "save": 0, "bug": 0, "inbox": 0, "outbox": 0,
}
# Fallbacks use only well-supported Geometric Shapes / Dingbats glyphs so they
# render as clean monochrome marks on Discord (no broken boxes) before the custom
# emoji images are uploaded. They repeat by design; the uploaded pack gives the
# distinct icons.
_EMOJI_FALLBACK = {
    "check": "✓", "cross": "✗", "warn": "▲", "info": "◉", "alert": "◆", "star": "★",
    "ticket": "▭", "crown": "◆", "lock": "■", "unlock": "□", "key": "◈", "shop": "▦",
    "cart": "▥", "gift": "✦", "wave": "◡", "bot": "◙", "pin": "◆", "tack": "◇",
    "clock": "○", "hourglass": "▽", "chart": "▦", "tool": "◈", "gear": "◉", "trash": "✗",
    "link": "◇", "coin": "◎", "shield": "◈", "user": "◉", "users": "◎", "roles": "◈",
    "chat": "◗", "note": "▤", "edit": "▤", "package": "▣", "receipt": "▤", "screen": "▭",
    "bell": "◐", "zap": "▲", "rocket": "➤", "scroll": "▱", "clip": "◇", "calendar": "▦",
    "gem": "◆", "globe": "◎", "test": "◇", "ban": "○", "game": "◙", "announce": "▶",
    "money": "◎", "plus": "+", "minus": "-", "image": "▧", "film": "▶", "mail": "▭",
    "book": "▥", "file": "▭", "folder": "▭", "home": "◆", "idea": "○", "refresh": "○",
    "sound": "◀", "mute": "◁", "trophy": "▲", "search": "○", "fire": "▲", "flag": "▸",
    "clean": "✗", "door": "▯", "clipboard": "▦", "id": "▭", "hashtag": "#", "scale": "◆",
    "seed": "○", "save": "▤", "bug": "◈", "inbox": "▽", "outbox": "△",
}


def _emoji(name: str) -> str:
    """Custom emoji <:xzx_name:id> when an ID is set, else the monochrome fallback."""
    eid = _EMOJI_IDS.get(name, 0)
    return f"<:xzx_{name}:{eid}>" if eid else _EMOJI_FALLBACK.get(name, "")


E = SimpleNamespace(**{_n: _emoji(_n) for _n in _EMOJI_FALLBACK})


def resolve_emojis(emojis) -> int:
    """Switch the registry over to uploaded custom emojis automatically.

    Pass the bot's emojis (bot.emojis) on ready. Any emoji named ``xzx_<name>`` that
    matches a registry entry is wired in live - no manual ID editing needed. Entries
    with no uploaded match keep their monochrome fallback. Returns how many resolved."""
    by_name = {e.name: e for e in emojis}
    found = 0
    for name in _EMOJI_FALLBACK:
        emoji = by_name.get(f"xzx_{name}")
        if emoji is not None:
            _EMOJI_IDS[name] = emoji.id
            setattr(E, name, f"<{'a' if getattr(emoji, 'animated', False) else ''}:xzx_{name}:{emoji.id}>")
            found += 1
    return found


# Reverse map so stored/config emojis (admin-set ticket types, shop items, seeded
# defaults) join the theme too. Keys are base forms with any VS16 selector stripped.
_RAW_TO_NAME = {"✅": "check", "❌": "cross", "⚠": "warn", "ℹ": "info", "🚨": "alert", "⭐": "star",
    "★": "star", "🎫": "ticket", "👑": "crown", "🔒": "lock", "🔐": "lock", "🔓": "unlock",
    "🔑": "key", "🛍": "shop", "🛒": "cart", "🎉": "gift", "🎁": "gift", "👋": "wave",
    "🤖": "bot", "📍": "pin", "📌": "tack", "🕒": "clock", "⏰": "clock", "🕐": "clock",
    "⏳": "hourglass", "⌛": "hourglass", "📊": "chart", "📈": "chart", "🛠": "tool", "🔧": "tool",
    "🔨": "tool", "⚙": "gear", "🗑": "trash", "🔗": "link", "🪙": "coin", "🛡": "shield",
    "👤": "user", "👥": "users", "🙋": "users", "🎭": "roles", "💬": "chat", "📝": "note",
    "✏": "edit", "✍": "edit", "📦": "package", "🧾": "receipt", "🖥": "screen", "🔔": "bell",
    "🔕": "bell", "⚡": "zap", "🚀": "rocket", "📜": "scroll", "📎": "clip", "📅": "calendar",
    "🗓": "calendar", "💎": "gem", "🌐": "globe", "🌍": "globe", "🧪": "test", "🚫": "ban",
    "⛔": "ban", "🚷": "ban", "🎮": "game", "📢": "announce", "📣": "announce", "💰": "money",
    "💲": "money", "💸": "money", "➕": "plus", "➖": "minus", "🖼": "image", "🎬": "film",
    "🎞": "film", "📬": "mail", "📭": "mail", "📪": "mail", "📩": "mail", "📨": "mail",
    "✉": "mail", "📧": "mail", "📚": "book", "📖": "book", "📄": "file", "📃": "file",
    "📑": "file", "📁": "folder", "📂": "folder", "🗂": "folder", "🏠": "home", "💡": "idea",
    "🔄": "refresh", "🔁": "refresh", "🔊": "sound", "🔇": "mute", "🏆": "trophy", "🥇": "trophy",
    "🏅": "trophy", "🔍": "search", "🔎": "search", "🕵": "search", "🔥": "fire", "🚩": "flag",
    "🏁": "flag", "🧹": "clean", "🚪": "door", "📋": "clipboard", "🆔": "id", "🔢": "hashtag",
    "⚖": "scale", "🌱": "seed", "💾": "save", "🐛": "bug", "📥": "inbox", "📤": "outbox",
}


def themed(stored) -> str:
    """Display form of a stored/config emoji: its registry glyph (monochrome fallback
    now, custom image once uploaded) when it's a known emoji, else the stored string
    unchanged. Safe anywhere custom emojis render - card and embed text."""
    if not stored:
        return ""
    name = _RAW_TO_NAME.get(stored) or _RAW_TO_NAME.get(stored.replace("️", ""))
    return getattr(E, name) if name else stored


def themed_component(stored):
    """emoji= form for a button or select option: the custom emoji once its image is
    uploaded, else the original stored emoji (always a valid Discord emoji). Never the
    monochrome fallback, which Discord can reject as a component emoji."""
    if not stored:
        return None
    name = _RAW_TO_NAME.get(stored) or _RAW_TO_NAME.get(stored.replace("️", ""))
    if name and _EMOJI_IDS.get(name):
        return f"<:xzx_{name}:{_EMOJI_IDS[name]}>"
    return stored


UNITS = {"s": 1, "m": 60, "h": 3600, "d": 86400}
HEX_RE = re.compile(r"^#?([0-9a-fA-F]{6})$")


class UserError(Exception):
    """A user-facing error. The bot shows the message as an ephemeral reply."""


def parse_duration(text: str) -> int | None:
    """Turn '90s', '10m', '2h30m' or '1d' into seconds (None if it isn't valid)."""
    cleaned = re.sub(r"\s+", "", text.lower())
    matches = re.findall(r"(\d+)([smhd])", cleaned)
    if not matches or "".join(f"{n}{u}" for n, u in matches) != cleaned:
        return None
    return sum(int(n) * UNITS[u] for n, u in matches)


def parse_color(text: str) -> int:
    match = HEX_RE.match(text.strip())
    if not match:
        raise UserError("Colour must be a hex code like `#5865F2`.")
    return int(match[1], 16)


def ordinal(n: int) -> str:
    if 10 <= n % 100 <= 20:
        suffix = "th"
    else:
        suffix = {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")
    return f"{n:,}{suffix}"


def render(text: str, member: discord.Member, mention: bool = True) -> str:
    """Fill in {user} {username} {server} {count} {ordinal} placeholders."""
    guild = member.guild
    count = guild.member_count or 0
    return (
        text.replace("{user}", member.mention if mention else member.display_name)
        .replace("{username}", member.display_name)
        .replace("{server}", guild.name)
        .replace("{count}", f"{count:,}")
        .replace("{ordinal}", ordinal(count))
    )


def check_role(interaction: discord.Interaction, role: discord.Role) -> None:
    """Make sure a role is safe to hand out and that both the bot and the admin can manage it."""
    guild = interaction.guild
    if role.is_default() or role.managed:
        raise UserError("Pick a normal role (not @everyone, a bot role or an integration role).")
    if role.permissions.administrator:
        raise UserError("For safety I won't hand out a role that has Administrator permission.")
    if role >= guild.me.top_role:
        raise UserError("My highest role must sit **above** that role. Drag my role higher in Server Settings → Roles.")
    if interaction.user != guild.owner and role >= interaction.user.top_role:
        raise UserError("You can only use roles that are below your own highest role.")


def check_target(interaction: discord.Interaction, member: discord.Member) -> None:
    """Make sure the admin and the bot are allowed to moderate this member."""
    guild = interaction.guild
    if member == interaction.user:
        raise UserError("You can't do that to yourself.")
    if member.id == guild.owner_id:
        raise UserError("You can't do that to the server owner.")
    if member == guild.me:
        raise UserError("Nice try.")
    if interaction.user.id != guild.owner_id and member.top_role >= interaction.user.top_role:
        raise UserError("That member's top role is equal to or higher than yours.")
    if member.top_role >= guild.me.top_role:
        raise UserError("That member's top role is equal to or higher than mine. Move my role higher.")


def compact(**kwargs) -> dict:
    """Drop None values so they aren't passed to discord.py send/edit calls."""
    return {k: v for k, v in kwargs.items() if v is not None}


def v2(kwargs: dict) -> dict:
    """Normalize a raw send/DM kwargs dict for Components V2.

    ui.card()/ui.note()/card_builder().build() return a CardView (a LayoutView),
    not a discord.Embed. If such a CardView is passed under 'embed', discord.py
    calls Embed.to_dict() on it and raises AttributeError. Move it to 'view',
    merging any interactive view already in the dict into the card's ActionRows
    via with_view. No-op for a real embed, a missing/None embed, or a dict that
    never carried one. Use at raw channel.send(**kwargs) / user.send(**kwargs)
    sites that bypass reply()."""
    card = kwargs.get("embed")
    if card is None:
        return kwargs
    try:
        from ui import CardView  # local import to avoid circular
    except ImportError:
        return kwargs
    if isinstance(card, CardView):
        kwargs["view"] = card.with_view(kwargs.pop("view", None))
        del kwargs["embed"]
    return kwargs


async def reply(interaction: discord.Interaction, **kwargs):
    """Respond to an interaction whether or not it has been answered yet (ephemeral by default).

    Supports Components V2: if 'embed' kwarg is a CardView (from ui.card/ui.note),
    it is automatically moved to 'view' and Components V2 flags are set.
    """
    # Detect CardView passed as 'embed' for backward compat with call sites
    _maybe_card = kwargs.get("embed")
    if _maybe_card is not None:
        try:
            from ui import CardView  # local import to avoid circular
            if isinstance(_maybe_card, CardView):
                kwargs["view"] = _maybe_card
                del kwargs["embed"]
        except ImportError:
            pass

    # If a CardView is in 'view', strip 'embeds'/'content' conflicts and set V2 flags
    _view = kwargs.get("view")
    if _view is not None:
        try:
            from ui import CardView
            if isinstance(_view, CardView):
                kwargs.pop("embeds", None)
                # content is allowed alongside V2 but keep it clean
        except ImportError:
            pass

    kwargs = compact(**kwargs)
    kwargs.setdefault("ephemeral", True)
    if interaction.response.is_done():
        return await interaction.followup.send(**kwargs)
    return await interaction.response.send_message(**kwargs)


def check_can_send(channel: discord.TextChannel, me: discord.Member, files: bool = False) -> None:
    perms = channel.permissions_for(me)
    ok = perms.view_channel and perms.send_messages and perms.embed_links and (perms.attach_files if files else True)
    if not ok:
        needed = "View Channel, Send Messages, Embed Links" + (" and Attach Files" if files else "")
        raise UserError(f"I need {needed} in {channel.mention}.")


def staff_ids(cfg) -> list[int]:
    return [int(x) for x in (cfg["staff_roles"] or "").split(",") if x.strip().isdigit()]


def is_staff(member: discord.Member, cfg) -> bool:
    if member.guild_permissions.manage_guild:
        return True
    ids = set(staff_ids(cfg))
    return any(r.id in ids for r in member.roles)


def support_button(guild: discord.Guild, cfg):
    """A link button back to the support/ticket panel channel, for DMs. None if no panel is set up."""
    if not cfg or not cfg["panel_channel_id"]:
        return None
    return discord.ui.Button(
        style=discord.ButtonStyle.link, label="Support", emoji="🎫", url=f"https://discord.com/channels/{guild.id}/{cfg['panel_channel_id']}",
    )


# A link (usually a Stripe Payment Link) pasted where a price belongs. Never shown as a price.
LINK_RE = re.compile(r"(https?://|www\.|buy\.stripe\.com|discord\.gg/)", re.I)
