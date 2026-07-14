"""OG image generation for public card pages.

Renders 1200×630 PNG matching the card's bg + photo + name + membership_no.
Uses Pillow + Manrope variable font. Output is bytes — caller adds caching.
"""

from __future__ import annotations

import contextlib
import io
import logging
import math
import re
from functools import lru_cache
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw, ImageFont

from std_cards.core.color import _hex_to_rgb, contrast_palette, is_light_color

logger = logging.getLogger(__name__)

OG_W = 1200
OG_H = 630

PUBLIC_DIR = Path(__file__).resolve().parent.parent / "public"
FONT_PATH = PUBLIC_DIR / "fonts" / "Manrope-Variable.ttf"
EMBLEM_DARK_PATH = PUBLIC_DIR / "og-emblem-dark.png"
EMBLEM_WHITE_PATH = PUBLIC_DIR / "og-emblem-white.png"

_HEX_RE = re.compile(r"^#[0-9A-Fa-f]{6}$")


@lru_cache(maxsize=64)
def _font(size: int, weight: str = "Regular") -> ImageFont.FreeTypeFont:
    f = ImageFont.truetype(str(FONT_PATH), size=size)
    with contextlib.suppress(OSError):
        f.set_variation_by_name(weight)
    return f


@lru_cache(maxsize=2)
def _emblem(white: bool) -> Image.Image:
    path = EMBLEM_WHITE_PATH if white else EMBLEM_DARK_PATH
    return Image.open(path).convert("RGBA")


def _safe_hex(value: str | None, fallback: str) -> str:
    if value and _HEX_RE.match(value):
        return value
    return fallback


def _draw_background(canvas: Image.Image, card: dict[str, Any]) -> str:
    """Draw bg gradient or solid. Return hex of palette anchor."""
    fallback = "#1F1E5E"
    bg_kind = card.get("bg_kind", "solid")
    bg_color = _safe_hex(card.get("bg_color"), fallback)
    if bg_kind != "gradient":
        canvas.paste(_hex_to_rgb(bg_color), (0, 0, OG_W, OG_H))
        return bg_color

    g = card.get("bg_gradient") or {}
    from_hex = _safe_hex(g.get("from") or g.get("start"), fallback)
    to_hex = _safe_hex(g.get("to") or g.get("end"), "#798BFF")
    try:
        angle = int(g.get("angle", 180))
        if angle < 0 or angle > 360:
            angle = 180
    except (TypeError, ValueError):
        angle = 180

    from_rgb = _hex_to_rgb(from_hex)
    to_rgb = _hex_to_rgb(to_hex)

    rad = math.radians(angle - 90)
    dx, dy = math.cos(rad), math.sin(rad)
    half_diag = (OG_W**2 + OG_H**2) ** 0.5 / 2
    cx, cy = OG_W / 2, OG_H / 2

    px = canvas.load()
    for y in range(OG_H):
        for x in range(OG_W):
            t = ((x - cx) * dx + (y - cy) * dy) / (2 * half_diag) + 0.5
            t = max(0.0, min(1.0, t))
            r = int(from_rgb[0] + (to_rgb[0] - from_rgb[0]) * t)
            g_ = int(from_rgb[1] + (to_rgb[1] - from_rgb[1]) * t)
            b = int(from_rgb[2] + (to_rgb[2] - from_rgb[2]) * t)
            px[x, y] = (r, g_, b)

    return from_hex


def _draw_photo_or_initials(
    canvas: Image.Image,
    photo_bytes: bytes | None,
    initials: str,
    photo_shape: str,
    palette: dict[str, str],
    box: tuple[int, int, int, int],
) -> None:
    """Draw photo (or initials placeholder) inside box (x0, y0, x1, y1)."""
    x0, y0, x1, y1 = box
    size = x1 - x0
    radius = 32 if photo_shape == "square" else size // 2

    is_dark_bg = is_light_color(palette["text"])
    mask = Image.new("L", (size, size), 0)
    ImageDraw.Draw(mask).rounded_rectangle((0, 0, size - 1, size - 1), radius=radius, fill=255)

    if photo_bytes:
        try:
            photo = Image.open(io.BytesIO(photo_bytes)).convert("RGBA")
            sw, sh = photo.size
            scale = max(size / sw, size / sh)
            photo = photo.resize((int(sw * scale), int(sh * scale)), Image.LANCZOS)
            cx = (photo.size[0] - size) // 2
            cy = (photo.size[1] - size) // 2
            photo = photo.crop((cx, cy, cx + size, cy + size))
            canvas.paste(photo, (x0, y0), mask)
            return
        except Exception:
            logger.exception("og: failed to render photo, fallback to initials")

    overlay = Image.new("RGBA", (OG_W, OG_H), (0, 0, 0, 0))
    od = ImageDraw.Draw(overlay)
    fill = (255, 255, 255, 50) if is_dark_bg else (2, 6, 23, 30)
    od.rounded_rectangle((x0, y0, x1, y1), radius=radius, fill=fill)
    canvas.alpha_composite(overlay)

    init_color = (255, 255, 255, 230) if is_dark_bg else (2, 6, 23, 230)
    init_font = _font(int(size * 0.42), "ExtraBold")
    d = ImageDraw.Draw(canvas)
    d.text(
        (x0 + size // 2, y0 + size // 2),
        initials,
        font=init_font,
        fill=init_color,
        anchor="mm",
    )


def _shrink_to_fit(text: str, max_width: int, max_size: int, min_size: int = 32) -> int:
    for size in range(max_size, min_size - 1, -4):
        f = _font(size, "ExtraBold")
        bbox = f.getbbox(text)
        if bbox[2] - bbox[0] <= max_width:
            return size
    return min_size


def _draw_text_block(
    canvas: Image.Image,
    card: dict[str, Any],
    palette: dict[str, str],
    text_x: int,
    text_max_width: int,
    text_color_main: tuple[int, int, int, int],
    text_color_muted: tuple[int, int, int, int],
) -> None:
    d = ImageDraw.Draw(canvas)
    cur_y = 90

    use_white_emblem = is_light_color(palette["text"])
    emblem = _emblem(use_white_emblem).resize((56, 56), Image.LANCZOS)
    canvas.paste(emblem, (text_x, cur_y), emblem)
    org_font = _font(20, "Regular")
    d.text(
        (text_x + 72, cur_y + 4),
        "СОЮЗ ТЕАТРАЛЬНЫХ ДЕЯТЕЛЕЙ\nРОССИЙСКОЙ ФЕДЕРАЦИИ",
        font=org_font,
        fill=text_color_muted,
        spacing=4,
    )
    cur_y += 80

    cur_y += 32
    membership = f"Членский билет №{card.get('membership_no', '—')}"
    mem_font = _font(28, "Regular")
    d.text((text_x, cur_y), membership, font=mem_font, fill=text_color_muted)
    cur_y += 56

    full_name = (
        " ".join(
            filter(None, [card.get("last_name"), card.get("first_name"), card.get("middle_name")])
        ).upper()
        or "—"
    )
    name_size = _shrink_to_fit(full_name, text_max_width, 56, 32)
    name_font = _font(name_size, "ExtraBold")
    name_lines = _wrap_text(full_name, name_font, text_max_width, max_lines=2)
    for line in name_lines:
        d.text((text_x, cur_y), line, font=name_font, fill=text_color_main)
        cur_y += int(name_size * 1.2)

    cur_y += 16
    sub_font = _font(22, "Regular")
    d.text((text_x, cur_y), "Член союза театральных деятелей", font=sub_font, fill=text_color_muted)

    footer_font = _font(20, "Regular")
    footer_text = "stdrf.ru"
    bbox = footer_font.getbbox(footer_text)
    fw = bbox[2] - bbox[0]
    d.text((OG_W - 80 - fw, OG_H - 80 - 22), footer_text, font=footer_font, fill=text_color_muted)


def _wrap_text(
    text: str, font: ImageFont.FreeTypeFont, max_w: int, max_lines: int = 2
) -> list[str]:
    words = text.split()
    lines: list[str] = []
    cur = ""
    for w in words:
        candidate = (cur + " " + w).strip()
        bbox = font.getbbox(candidate)
        if bbox[2] - bbox[0] <= max_w:
            cur = candidate
        else:
            if cur:
                lines.append(cur)
            cur = w
            if len(lines) >= max_lines:
                break
    if cur and len(lines) < max_lines:
        lines.append(cur)
    if len(lines) > max_lines:
        lines = lines[:max_lines]
        last = lines[-1]
        while font.getbbox(last + "…")[2] > max_w and len(last) > 0:
            last = last[:-1]
        lines[-1] = last + "…"
    return lines


def _palette_to_rgba(rgba_or_hex: str) -> tuple[int, int, int, int]:
    if rgba_or_hex.startswith("#"):
        r, g, b = _hex_to_rgb(rgba_or_hex)
        return (r, g, b, 255)
    if rgba_or_hex.startswith("rgba"):
        nums = rgba_or_hex[5:-1].split(",")
        r, g, b = (int(x.strip()) for x in nums[:3])
        a = int(float(nums[3].strip()) * 255)
        return (r, g, b, a)
    return (255, 255, 255, 255)


def _initials(card: dict[str, Any]) -> str:
    last = (card.get("last_name") or "").strip()
    first = (card.get("first_name") or "").strip()
    return ((last[:1] or "") + (first[:1] or "")).upper() or "СТД"


def render_card_og(card: dict[str, Any], photo_bytes: bytes | None = None) -> bytes:
    """Render 1200×630 OG image for the given card. Returns PNG bytes."""
    canvas = Image.new("RGB", (OG_W, OG_H), "#1F1E5E")
    bg_anchor = _draw_background(canvas, card)
    canvas = canvas.convert("RGBA")

    palette = contrast_palette(bg_anchor)
    text_main = _palette_to_rgba(palette["text"])
    text_muted = _palette_to_rgba(palette["text_muted"])

    photo_box = (80, (OG_H - 320) // 2, 80 + 320, (OG_H - 320) // 2 + 320)
    _draw_photo_or_initials(
        canvas,
        photo_bytes,
        _initials(card),
        card.get("photo_shape", "square"),
        palette,
        photo_box,
    )

    text_x = 80 + 320 + 60
    text_max_width = OG_W - text_x - 80
    _draw_text_block(canvas, card, palette, text_x, text_max_width, text_main, text_muted)

    out = io.BytesIO()
    canvas.convert("RGB").save(out, format="PNG", optimize=True)
    return out.getvalue()
