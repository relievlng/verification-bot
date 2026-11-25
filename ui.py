"""One look for every message: Components V2 containers with accent colors, tidy key/value blocks, star helpers."""
from typing import Iterable, Optional

import discord

from common import ACCENT, COLOR, DANGER, INFO, SUCCESS, WARN  # noqa: F401  (re-exported for convenience)

DIVIDER = "▬▬▬▬▬▬▬▬▬▬▬▬"
MEDALS = ["🥇", "🥈", "🥉"]


def stars(value: float, total: int = 5) -> str:
    filled = max(0, min(total, int(round(value))))
    return "★" * filled + "☆" * (total - filled)


def rating_line(average: Optional[float], count: int) -> str:
    if not count:
        return "No reviews yet"
    return f"{stars(average or 0)} **{average:.1f}** ({count})"


def plural(n: int, word: str, many: Optional[str] = None) -> str:
    return f"{n:,} {word if n == 1 else (many or word + 's')}"


def bar(fraction: float, width: int = 10) -> str:
    filled = max(0, min(width, int(round(fraction * width))))
    return "█" * filled + "░" * (width - filled)


def kv(*pairs: tuple) -> str:
    """Tidy 'label * value' lines. Pairs with an empty value are skipped."""
    return "\n".join(f"**{label}** - {value}" for label, value in pairs if value not in (None, ""))


def duration(seconds: float) -> str:
    seconds = int(seconds)
    if seconds < 60:
        return f"{seconds}s"
    minutes = seconds // 60
    if minutes < 60:
        return f"{minutes}m"
    hours, minutes = divmod(minutes, 60)
    if hours < 48:
        return f"{hours}h {minutes}m"
    return f"{hours // 24}d {hours % 24}h"


def rank(i: int) -> str:
    return MEDALS[i] if i < len(MEDALS) else f"`{i + 1}.`"


# ---------------------------------------------------------------- V2 helpers ----


def _build_text(title: Optional[str], description: Optional[str], footer: Optional[str],
                guild: Optional[discord.Guild], section: Optional[str],
                thumbnail: Optional[str], image: Optional[str],
                author: Optional[tuple], fields: Optional[list] = None) -> str:
    """Compose a markdown string from embed-like parts."""
    parts = []
    if author:
        name = author[0]
        parts.append(f"**{name}**")
    if thumbnail:
        # In Components V2 we can reference thumbnails via Section accessory or just mention them in text
        # We'll handle thumbnail specially in container()
        pass
    if title:
        parts.append(f"### {title}")
    if description:
        parts.append(description)
    if fields:
        for name, value, inline in fields:
            if name and value:
                parts.append(f"**{name}**\n{value}")
    footer_text = footer or (" - ".join(x for x in (guild.name if guild else None, section) if x) or None)
    if footer_text:
        parts.append(f"-# {footer_text}")
    return "\n\n".join(p for p in parts if p)


class CardView(discord.ui.LayoutView):
    """A Components V2 layout view that wraps a single container card."""

    def __init__(
        self,
        text_content: str,
        *,
        color: discord.Color | int = COLOR,
        thumbnail_url: Optional[str] = None,
        image_url: Optional[str] = None,
        extra_views: Optional[list] = None,
    ):
        super().__init__()
        accent = color if isinstance(color, discord.Color) else discord.Color(color)
        children: list = []

        if thumbnail_url:
            # Use a Section with Thumbnail accessory for the top part
            section = discord.ui.Section(
                discord.ui.TextDisplay(text_content),
                accessory=discord.ui.Thumbnail(thumbnail_url),
            )
            children.append(section)
        else:
            children.append(discord.ui.TextDisplay(text_content))

        if image_url:
            gallery = discord.ui.MediaGallery()
            gallery.add_item(media=image_url)
            children.append(gallery)

        self.container = discord.ui.Container(*children, accent_color=accent)
        self.add_item(self.container)

        # Attach any extra interactive items wrapped in ActionRows (V2 requirement)
        if extra_views:
            for i in range(0, max(1, len(extra_views)), 5):
                row_items = extra_views[i:i + 5]
                if row_items:
                    self.add_item(discord.ui.ActionRow(*row_items))

    def with_view(self, other: "discord.ui.View | None") -> "CardView":
        """Merge another View's interactive items (buttons, selects) into this LayoutView.

        Components V2 only allows one view= per message. When a card and an
        interactive view must both appear, call card.with_view(interactive_view)
        and pass the result as the sole view= argument.

        In V2, interactive items must live inside ActionRows, and ActionRows
        are added directly to the LayoutView (not to any Container inside it).
        """
        if other is None:
            return self
        # Group children into ActionRows of up to 5 items each
        children = list(other.children)
        for i in range(0, max(1, len(children)), 5):
            row_items = children[i:i + 5]
            if not row_items:
                break
            action_row = discord.ui.ActionRow(*row_items)
            self.add_item(action_row)
        return self

    # ------------------------------------------------------------------ compat shims --
    # Allow incremental building on a CardView (mirrors discord.Embed's API).
    # These collect extra text and rebuild the TextDisplay on the fly.

    def _append_text(self, extra: str) -> None:
        """Append a markdown block to the card's TextDisplay in place."""
        # Find the TextDisplay to update
        td = None
        for child in self.container.children:
            if isinstance(child, discord.ui.TextDisplay):
                td = child
                break
            if isinstance(child, discord.ui.Section):
                for sc in child.children:
                    if isinstance(sc, discord.ui.TextDisplay):
                        td = sc
                        break
        if td is None:
            self.container.add_item(discord.ui.TextDisplay(extra))
        else:
            td.content = (td.content or "") + "\n\n" + extra

    def add_field(self, *, name: str, value: str, inline: bool = True) -> "CardView":
        self._append_text(f"**{name}**\n{value}")
        return self

    def set_footer(self, *, text: str, icon_url: Optional[str] = None) -> "CardView":
        self._append_text(f"-# {text}")
        return self

    def set_thumbnail(self, *, url: str) -> "CardView":
        # Can't add a second thumbnail retroactively; store for reference only
        return self

    def set_image(self, *, url: str) -> "CardView":
        try:
            gallery = discord.ui.MediaGallery()
            gallery.add_item(media=url)
            self.container.add_item(gallery)
        except Exception:
            pass
        return self

    def set_author(self, *, name: str, url: Optional[str] = None, icon_url: Optional[str] = None) -> "CardView":
        self._append_text(f"**{name}**")
        return self

    @property
    def description(self) -> str:
        """Compat: read the TextDisplay content."""
        for child in self.container.children:
            if isinstance(child, discord.ui.TextDisplay):
                return child.content or ""  
            if isinstance(child, discord.ui.Section):
                for sc in child.children:
                    if isinstance(sc, discord.ui.TextDisplay):
                        return sc.content or ""  
        return ""

    @description.setter
    def description(self, value: str) -> None:
        """Compat: replace the TextDisplay content."""
        for child in self.container.children:
            if isinstance(child, discord.ui.TextDisplay):
                child.content = value  
                return
            if isinstance(child, discord.ui.Section):
                for sc in child.children:
                    if isinstance(sc, discord.ui.TextDisplay):
                        sc.content = value  
                        return
        self.container.add_item(discord.ui.TextDisplay(value))

    @property
    def url(self) -> Optional[str]:
        """Compat stub - V2 containers don't have URLs."""
        return None

    @url.setter
    def url(self, value: Optional[str]) -> None:
        """Compat stub - no-op for V2."""

    @property
    def title(self) -> str:
        """Return the first ### heading from the TextDisplay, or empty string."""
        for line in self.description.split('\n'):
            if line.startswith('### '):
                return line[4:]
        return ""

    @title.setter
    def title(self, value: str) -> None:
        """Replace or prepend a ### heading in the TextDisplay."""
        desc = self.description
        lines = desc.split('\n')
        for i, line in enumerate(lines):
            if line.startswith('### '):
                lines[i] = f"### {value}"
                self.description = '\n'.join(lines)
                return
        # No existing heading - prepend
        new_desc = f"### {value}\n\n{desc}".strip()
        self.description = new_desc


def card(
    title: Optional[str] = None,
    description: Optional[str] = None,
    *,
    color: discord.Color | int = COLOR,
    guild: Optional[discord.Guild] = None,
    section: Optional[str] = None,
    footer: Optional[str] = None,
    thumbnail: Optional[str] = None,
    image: Optional[str] = None,
    author: Optional[tuple] = None,
    timestamp: bool = False,
    _fields: Optional[list] = None,
) -> "CardView":
    """
    Build a Components V2 CardView (replaces discord.Embed).
    Returns a CardView - pass as `view=card(...)` instead of `embed=card(...)`.

    For backward compat with .add_field() callers: use card_builder() instead.
    """
    text = _build_text(title, description, footer, guild, section, thumbnail, image, author, _fields)
    return CardView(text or "​", color=color, thumbnail_url=thumbnail, image_url=image)


def note(title: str, text: str, color: discord.Color | int = COLOR) -> "CardView":
    """A small status message (errors, confirmations). Returns CardView."""
    return card(title, text, color=color)


class CardBuilder:
    """
    Mutable card builder that supports .add_field() and .set_* calls,
    for code paths that build embeds incrementally.
    Call .build() to get the final CardView.
    """

    def __init__(
        self,
        title: Optional[str] = None,
        description: Optional[str] = None,
        *,
        color: discord.Color | int = COLOR,
        guild: Optional[discord.Guild] = None,
        section: Optional[str] = None,
        footer: Optional[str] = None,
        thumbnail: Optional[str] = None,
        image: Optional[str] = None,
        author: Optional[tuple] = None,
    ):
        self.title = title
        self.description = description
        self.color = color
        self.guild = guild
        self.section = section
        self.footer = footer
        self.thumbnail = thumbnail
        self.image = image
        self.author = author
        self.fields: list = []

    def add_field(self, name: str, value: str, inline: bool = True) -> "CardBuilder":
        self.fields.append((name, value, inline))
        return self

    def set_footer(self, text: str, icon_url: Optional[str] = None) -> "CardBuilder":
        self.footer = text
        return self

    def set_thumbnail(self, url: str) -> "CardBuilder":
        self.thumbnail = url
        return self

    def set_image(self, url: str) -> "CardBuilder":
        self.image = url
        return self

    def set_author(self, name: str, icon_url: Optional[str] = None) -> "CardBuilder":
        self.author = (name, icon_url) if icon_url else (name,)
        return self

    def build(self) -> CardView:
        text = _build_text(
            self.title, self.description, self.footer,
            self.guild, self.section, self.thumbnail, self.image,
            self.author, self.fields or None,
        )
        return CardView(text or "​", color=self.color, thumbnail_url=self.thumbnail, image_url=self.image)


def card_builder(
    title: Optional[str] = None,
    description: Optional[str] = None,
    *,
    color: discord.Color | int = COLOR,
    guild: Optional[discord.Guild] = None,
    section: Optional[str] = None,
    footer: Optional[str] = None,
    thumbnail: Optional[str] = None,
    image: Optional[str] = None,
    author: Optional[tuple] = None,
) -> CardBuilder:
    """Return a CardBuilder for cases that need .add_field() style building."""
    return CardBuilder(
        title, description, color=color, guild=guild, section=section,
        footer=footer, thumbnail=thumbnail, image=image, author=author,
    )


# Keep a simple legacy alias so old Embed-typed type hints don't break at runtime
# (they're now CardView objects but Python doesn't enforce return-type annotations)
LegacyEmbed = CardView
