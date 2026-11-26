import time

import discord
from datetime import timedelta

import db
import ui
from common import ACCENT, COLOR, DANGER, INFO, SUCCESS, WARN, E

CATEGORIES = {
    "verification": "Verification events",
    "join": "Members joining",
    "leave": "Members leaving",
    "message_edit": "Edited messages",
    "message_delete": "Deleted messages",
    "role_create": "Roles created",
    "role_delete": "Roles deleted",
    "role_update": "Roles edited or given/taken from a member",
    "ban": "Bans and unbans",
    "kick": "Kicks",
    "timeout": "Timeouts",
    "warn": "Warnings",
    "channel_create": "Channels created",
    "channel_delete": "Channels deleted",
    "channel_update": "Channels edited, locked or slowed",
    "nicknames": "Nickname and username changes",
    "voice": "Voice channel activity",
    "server": "Server settings changes",
    "shop": "Shop purchases",
    "tickets": "Support tickets",
    "giveaways": "Giveaways",
    "invites": "Invites",
    "files": "File downloads",
    "automod": "Automod actions",
    "posts": "Posts and packs",
    "staff": "Staff actions",
    "commands": "Every slash command anyone runs",
    "events": "Scheduled server events",
    "keys": "Macro key logins and Discord links",
    "sharing": "Keys auto-disabled for use on a second device",
}


# Layout used by "Create log channels": one private channel per category, fully separated.
LOG_CHANNELS = {
    "verification": (f"{E.check}・verify-logs", "Verification attempts, passes and lockdown", ["verification"]),
    "join": (f"{E.wave}・join-logs", "Members joining", ["join"]),
    "leave": (f"{E.door}・leave-logs", "Members leaving", ["leave"]),
    "message_edit": (f"{E.edit}・edit-logs", "Edited messages", ["message_edit"]),
    "message_delete": (f"{E.trash}・delete-logs", "Deleted messages", ["message_delete"]),
    "role_create": (f"{E.roles}・role-created-logs", "Roles created", ["role_create"]),
    "role_delete": (f"{E.roles}・role-deleted-logs", "Roles deleted", ["role_delete"]),
    "role_update": (f"{E.roles}・role-updated-logs", "Roles edited, or given to / taken from a member", ["role_update"]),
    "ban": (f"{E.tool}・ban-logs", "Bans and unbans", ["ban"]),
    "kick": ("👢・kick-logs", "Kicks", ["kick"]),
    "timeout": (f"{E.hourglass}・timeout-logs", "Timeouts", ["timeout"]),
    "warn": (f"{E.warn}・warn-logs", "Warnings", ["warn"]),
    "channel_create": (f"{E.folder}・channel-created-logs", "Channels created", ["channel_create"]),
    "channel_delete": (f"{E.folder}・channel-deleted-logs", "Channels deleted", ["channel_delete"]),
    "channel_update": (f"{E.folder}・channel-updated-logs", "Channels edited, locked or slowed", ["channel_update"]),
    "nicknames": (f"{E.edit}・name-logs", "Nickname and username changes", ["nicknames"]),
    "voice": (f"{E.sound}・voice-logs", "Voice channel activity", ["voice"]),
    "server": (f"{E.gear}・server-logs", "Server settings and emoji changes", ["server"]),
    "shop": (f"{E.cart}・shop-logs", "Shop purchases", ["shop"]),
    "tickets": (f"{E.ticket}・ticket-logs", "Support tickets", ["tickets"]),
    "giveaways": (f"{E.gift}・giveaway-logs", "Giveaways", ["giveaways"]),
    "invites": (f"{E.mail}・invite-logs", "Invites created, deleted and used", ["invites"]),
    "files": (f"{E.inbox}・file-logs", "File downloads", ["files"]),
    "automod": (f"{E.bot}・automod-logs", "Automod actions", ["automod"]),
    "posts": (f"{E.announce}・post-logs", "Posts and packs", ["posts"]),
    "staff": (f"{E.tool}・staff-logs", "Staff actions", ["staff"]),
    "commands": ("⌨️・command-logs", "Every slash command anyone runs", ["commands"]),
    "events": (f"{E.calendar}・event-logs", "Scheduled server events", ["events"]),
    "keys": (f"{E.key}・key-logs", "Macro key logins, refused keys and Discord links", ["keys"]),
    "sharing": (f"{E.alert}・shared-key-logs", "Keys auto-disabled for being used on a second device", ["sharing"]),
}
ESSENTIALS = {"join", "leave", "message_edit", "message_delete", "ban", "kick", "timeout", "warn", "verification", "tickets", "role_create", "role_delete", "role_update"}
HISTORY_DAYS = 30


def clip(text: str | None, limit: int = 1000) -> str:
    text = text or "—"
    return text if len(text) <= limit else text[: limit - 1] + "…"


async def send_log(guild: discord.Guild, category: str, embed: "ui.CardView", view=None) -> bool:
    """Send a log card to the channel for this category (respecting toggles and routes).

    'embed' is a Components V2 CardView, so it ships as view=, not embed=. Any interactive
    view is merged into the card's ActionRows via with_view (a no-op when view is None).
    """
    cfg = await db.get_config(guild.id)
    if not cfg:
        return False
    route = await db.fetch_one(
        "SELECT channel_id, enabled FROM log_routes WHERE guild_id = ? AND category = ?", (guild.id, category)
    )
    if route and not route["enabled"]:
        return False
    channel_id = (route["channel_id"] if route else None) or cfg["log_channel_id"]
    if not channel_id:
        return False
    channel = guild.get_channel(channel_id)
    if channel is None:
        return False
    try:
        await channel.send(view=embed.with_view(view))
        return True
    except discord.HTTPException:
        return False


CATEGORY_STYLE = {
    "verification": (f"{E.check} Verification", SUCCESS), "join": (f"{E.wave} Joins", SUCCESS), "leave": (f"{E.door} Leaves", DANGER),
    "message_edit": (f"{E.edit} Edits", WARN), "message_delete": (f"{E.trash} Deletes", WARN),
    "role_create": (f"{E.roles} Role created", SUCCESS), "role_delete": (f"{E.roles} Role deleted", DANGER), "role_update": (f"{E.roles} Role updated", ACCENT),
    "ban": (f"{E.tool} Bans", DANGER), "kick": ("👢 Kicks", WARN), "timeout": (f"{E.hourglass} Timeouts", WARN), "warn": (f"{E.warn} Warnings", WARN),
    "channel_create": (f"{E.folder} Channel created", SUCCESS), "channel_delete": (f"{E.folder} Channel deleted", DANGER), "channel_update": (f"{E.folder} Channel updated", INFO),
    "nicknames": (f"{E.edit} Names", INFO), "voice": (f"{E.sound} Voice", ACCENT), "server": (f"{E.gear} Server", WARN),
    "shop": (f"{E.cart} Shop", SUCCESS), "tickets": (f"{E.ticket} Tickets", ACCENT), "giveaways": (f"{E.gift} Giveaways", ACCENT), "invites": (f"{E.link} Invites", INFO), "files": (f"{E.inbox} Files", INFO), "automod": (f"{E.bot} Automod", WARN), "posts": (f"{E.announce} Posts", INFO), "staff": (f"{E.tool} Staff", INFO),
    "commands": ("⌨️ Commands", INFO), "events": (f"{E.calendar} Events", ACCENT), "keys": (f"{E.key} Keys", ACCENT),
    "sharing": (f"{E.alert} Shared key", DANGER),
}


async def emit(
    guild: discord.Guild,
    category: str,
    title: str,
    description: str = "",
    color: discord.Color | None = None,
    fields: tuple = (),
    thumbnail: str | None = None,
    footer: str | None = None,
    author: tuple | None = None,
    subject: int | None = None,
    actor: discord.abc.User | None = None,
    ids: tuple = (),
) -> None:
    """Send one log entry. Every log has the same shape: what happened, who it's about, the staff member responsible,
    the relevant IDs and when it happened, with the category colour and a tidy footer."""
    label, category_color = CATEGORY_STYLE.get(category, (category.title(), INFO))
    if color is None or color == COLOR:
        color = category_color
    text = description or ""
    extras = []
    if actor is not None and "🛡️" not in text:
        extras.append(f"**{E.shield} Staff** · {actor.mention} (`{actor.id}`)")
    if "🆔" not in text:
        pairs = ([("member", subject)] if subject else []) + [(k, v) for k, v in ids if v is not None]
        if pairs:
            extras.append(f"**{E.id} IDs** · " + " · ".join(f"{k} `{v}`" for k, v in pairs))
    if "🕒" not in text:
        extras.append(f"**{E.clock} When** · {discord.utils.format_dt(discord.utils.utcnow(), 'f')}")
    description = (text + "\n" if text else "") + "\n".join(extras)
    embed = ui.card(
        title, clip(description, 3800) if description else None, color=color, author=author, thumbnail=thumbnail,
        footer=f"{label} · {footer}" if footer else label, guild=guild, timestamp=True,
    )
    for name, value in fields:
        embed.add_field(name=name, value=clip(value), inline=False)
    if await send_log(guild, category, embed):
        # Keep a short, searchable history (never message text, only the headline and mentions)
        await db.execute(
            "INSERT INTO log_history (guild_id, category, title, summary, subject_id, created_at) VALUES (?, ?, ?, ?, ?, ?)",
            (guild.id, category, title[:200], clip(description, 400) if description else None, subject, discord.utils.utcnow().isoformat()),
        )


# ---- commands log their own actions; the audit-log events skip those so nothing is logged twice ----
_handled: dict[tuple, float] = {}


def mark_handled(guild_id: int, user_id: int, action: str) -> None:
    _handled[(guild_id, user_id, action)] = time.monotonic()
    for key in [k for k, t in _handled.items() if time.monotonic() - t > 120]:
        _handled.pop(key, None)


def was_handled(guild_id: int, user_id: int, action: str, within: float = 30) -> bool:
    stamp = _handled.pop((guild_id, user_id, action), None)
    return stamp is not None and time.monotonic() - stamp <= within


async def action_log(guild: discord.Guild, category: str, title: str, *, target, actor, reason: str | None = None, color=None,
                     lines: tuple = (), ids: tuple = (), fields: tuple = ()) -> None:
    """A moderation-style log: the member, the staff member, the reason, the IDs and the time, always in the same order."""
    name = getattr(target, "display_name", None) or getattr(target, "name", None) or f"User {target.id}"
    mention = getattr(target, "mention", f"<@{target.id}>")
    description = ui.kv((f"{E.user} Member", f"{mention} (`{target.id}`)"), *lines, (f"{E.note} Reason", reason or "None given"))
    avatar = getattr(getattr(target, "display_avatar", None), "url", None)
    await emit(guild, category, title, description, color, fields, author=(name, avatar) if avatar else (name,), subject=target.id, actor=actor, ids=ids)


async def prune_history(days: int = HISTORY_DAYS) -> None:
    cutoff = (discord.utils.utcnow() - timedelta(days=days)).isoformat()
    await db.execute("DELETE FROM log_history WHERE created_at < ?", (cutoff,))


async def find_audit_entry(guild: discord.Guild, action: discord.AuditLogAction, target_id: int, within: int = 20):
    """Look for a recent audit-log entry about target_id (needs the View Audit Log permission)."""
    if not guild.me.guild_permissions.view_audit_log:
        return None
    try:
        async for entry in guild.audit_logs(limit=8, action=action):
            if entry.target is not None and entry.target.id == target_id:
                if (discord.utils.utcnow() - entry.created_at).total_seconds() <= within:
                    return entry
    except discord.HTTPException:
        pass
    return None
