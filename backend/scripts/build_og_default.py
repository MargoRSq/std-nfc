"""Generate frontend/public/og-default.png — branded OG for site root."""

from __future__ import annotations

import math
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

REPO_ROOT = Path(__file__).resolve().parents[2]
FONT = REPO_ROOT / "backend" / "src" / "std_cards" / "public" / "fonts" / "Manrope-Variable.ttf"
EMBLEM = REPO_ROOT / "backend" / "src" / "std_cards" / "public" / "og-emblem-white.png"
OUT = REPO_ROOT / "frontend" / "public" / "og-default.png"

W, H = 1200, 630
BG_FROM = (31, 30, 94)
BG_TO = (14, 13, 61)


def gradient_bg() -> Image.Image:
    img = Image.new("RGB", (W, H), BG_FROM)
    px = img.load()
    for y in range(H):
        t = y / H
        r = int(BG_FROM[0] + (BG_TO[0] - BG_FROM[0]) * t)
        g = int(BG_FROM[1] + (BG_TO[1] - BG_FROM[1]) * t)
        b = int(BG_FROM[2] + (BG_TO[2] - BG_FROM[2]) * t)
        for x in range(W):
            px[x, y] = (r, g, b)
    return img


def constellation(canvas: Image.Image, count: int = 60) -> None:
    import random

    random.seed(42)
    overlay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    od = ImageDraw.Draw(overlay)
    for _ in range(count):
        x = random.randint(0, W)
        y = random.randint(0, H)
        r = random.choice([1, 1, 1, 2, 2, 3])
        a = random.randint(40, 130)
        od.ellipse((x - r, y - r, x + r, y + r), fill=(255, 255, 255, a))
    canvas.alpha_composite(overlay)


def font(size: int, weight: str = "Regular") -> ImageFont.FreeTypeFont:
    f = ImageFont.truetype(str(FONT), size=size)
    try:
        f.set_variation_by_name(weight)
    except OSError:
        pass
    return f


def main() -> None:
    canvas = gradient_bg().convert("RGBA")
    constellation(canvas)

    emblem = Image.open(EMBLEM).convert("RGBA")
    emblem = emblem.resize((180, 180), Image.LANCZOS)
    emblem_x = (W - 180) // 2
    emblem_y = 90
    canvas.paste(emblem, (emblem_x, emblem_y), emblem)

    d = ImageDraw.Draw(canvas)

    org_font = font(26, "Regular")
    d.text((W // 2, emblem_y + 180 + 32), "СОЮЗ ТЕАТРАЛЬНЫХ ДЕЯТЕЛЕЙ", font=org_font, fill=(255, 255, 255, 200), anchor="mm")
    d.text((W // 2, emblem_y + 180 + 32 + 36), "РОССИЙСКОЙ ФЕДЕРАЦИИ", font=org_font, fill=(255, 255, 255, 200), anchor="mm")

    title_font = font(72, "ExtraBold")
    d.text((W // 2, 440), "ЭЛЕКТРОННЫЕ", font=title_font, fill=(255, 255, 255, 255), anchor="mm")
    d.text((W // 2, 520), "УДОСТОВЕРЕНИЯ", font=title_font, fill=(255, 255, 255, 255), anchor="mm")

    url_font = font(22, "Regular")
    d.text((W // 2, 590), "stdrf.ru", font=url_font, fill=(121, 139, 255, 255), anchor="mm")

    canvas.convert("RGB").save(OUT, format="PNG", optimize=True)
    print(f"saved {OUT} ({OUT.stat().st_size} bytes)")


if __name__ == "__main__":
    main()
