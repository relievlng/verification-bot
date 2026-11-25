import os
import re

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

# ---------------------------------------------------------------- Custom emojis ----
# Replace the placeholder IDs with your real custom emoji IDs.
# Format: "<:name:ID>" for static, "<a:name:ID>" for animated.
E_CHECK  = "<:xzx_check:1234567890000001>"   # green checkmark
E_CROSS  = "<:xzx_cross:1234567890000002>"   # red X
E_WARN   = "<:xzx_warn:1234567890000003>"    # yellow warning
E_INFO   = "<:xzx_info:1234567890000004>"    # blue info
E_STAR   = "<:xzx_star:1234567890000005>"    # star / rating
E_TICKET = "<:xzx_ticket:1234567890000006>"  # ticket / support
E_CROWN  = "<:xzx_crown:1234567890000007>"   # crown / premium
E_LOCK   = "<:xzx_lock:1234567890000008>"    # lock / security
E_KEY    = "<:xzx_key:1234567890000009>"     # key / license
E_SHOP   = "<:xzx_shop:1234567890000010>"    # shop / purchase
E_GIFT   = "<:xzx_gift:1234567890000011>"    # gift / giveaway
E_WAVE   = "<:xzx_wave:1234567890000012>"    # wave / welcome
E_BOT    = "<:xzx_bot:1234567890000013>"     # bot / verification
E_PIN    = "<:xzx_pin:1234567890000014>"     # pin / role
E_CLOCK  = "<:xzx_clock:1234567890000015>"   # clock / time
E_CHART  = "<:xzx_chart:1234567890000016>"   # chart / stats
E_TOOL   = "<:xzx_tool:1234567890000017>"    # wrench / setup
E_TRASH  = "<:xzx_trash:1234567890000018>"   # trash / delete
E_LINK   = "<:xzx_link:1234567890000019>"    # link / external
E_COIN   = "<:xzx_coin:1234567890000020>"    # coin / currency

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
