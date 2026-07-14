def _hex_to_rgb(value: str) -> tuple[int, int, int]:
    v = value.lstrip("#")
    if len(v) == 3:
        v = "".join(ch * 2 for ch in v)
    if len(v) != 6:
        return (31, 30, 94)
    try:
        return int(v[0:2], 16), int(v[2:4], 16), int(v[4:6], 16)
    except ValueError:
        return (31, 30, 94)


def _perceived_brightness(rgb: tuple[int, int, int]) -> float:
    r, g, b = rgb
    return (0.299 * r + 0.587 * g + 0.114 * b) / 255.0


def is_light_color(hex_color: str) -> bool:
    return _perceived_brightness(_hex_to_rgb(hex_color)) > 0.55


def contrast_palette(bg_hex: str) -> dict[str, str]:
    """Pick text/overlay colors that read well on the given card bg.

    Tuned for the white pill of the lang toggle to keep enough contrast in
    both directions: white on dark navy, near-black on bright green/yellow."""
    light = is_light_color(bg_hex)
    if light:
        return {
            "text": "#020617",
            "text_strong": "#020617",
            "text_muted": "rgba(2,6,23,0.65)",
            "placeholder_bg": "rgba(2,6,23,0.08)",
            "placeholder_stroke": "rgba(2,6,23,0.45)",
            "pill_value": "#1F1E5E",
            "pill_label": "#727272",
        }
    return {
        "text": "#FFFFFF",
        "text_strong": "#FFFFFF",
        "text_muted": "rgba(255,255,255,0.75)",
        "placeholder_bg": "rgba(255,255,255,0.15)",
        "placeholder_stroke": "rgba(255,255,255,0.6)",
        "pill_value": "#1F1E5E",
        "pill_label": "#727272",
    }
