export interface CardPalette {
  text: string;
  textStrong: string;
  textMuted: string;
  placeholderBg: string;
  placeholderStroke: string;
  pillValue: string;
  pillLabel: string;
}

function hexToRgb(value: string): [number, number, number] {
  let v = value.trim().replace(/^#/, "");
  if (v.length === 3) v = v.split("").map((c) => c + c).join("");
  if (v.length !== 6) return [31, 30, 94];
  const r = parseInt(v.slice(0, 2), 16);
  const g = parseInt(v.slice(2, 4), 16);
  const b = parseInt(v.slice(4, 6), 16);
  if (Number.isNaN(r) || Number.isNaN(g) || Number.isNaN(b)) return [31, 30, 94];
  return [r, g, b];
}

function perceivedBrightness([r, g, b]: [number, number, number]): number {
  return (0.299 * r + 0.587 * g + 0.114 * b) / 255;
}

export function isLightColor(hex: string): boolean {
  return perceivedBrightness(hexToRgb(hex)) > 0.55;
}

export function contrastPalette(bgHex: string): CardPalette {
  if (isLightColor(bgHex)) {
    return {
      text: "#020617",
      textStrong: "#020617",
      textMuted: "rgba(2,6,23,0.65)",
      placeholderBg: "rgba(2,6,23,0.08)",
      placeholderStroke: "rgba(2,6,23,0.45)",
      pillValue: "#1F1E5E",
      pillLabel: "#727272",
    };
  }
  return {
    text: "#FFFFFF",
    textStrong: "#FFFFFF",
    textMuted: "rgba(255,255,255,0.75)",
    placeholderBg: "rgba(255,255,255,0.15)",
    placeholderStroke: "rgba(255,255,255,0.6)",
    pillValue: "#1F1E5E",
    pillLabel: "#727272",
  };
}
