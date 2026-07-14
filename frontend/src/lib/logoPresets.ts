export const LOGO_PRESETS = [{ id: "std", name: "СТД РФ" }] as const;

export type LogoPresetId = (typeof LOGO_PRESETS)[number]["id"];

export const DEFAULT_LOGO_PRESET_ID: LogoPresetId = "std";

export const PRESET_PREFIX = "preset:";

export function isPresetKey(value: string | null | undefined): value is `preset:${LogoPresetId}` {
  return typeof value === "string" && value.startsWith(PRESET_PREFIX);
}

export function presetIdFromKey(value: string): string {
  return value.slice(PRESET_PREFIX.length);
}

export function makePresetKey(id: LogoPresetId): string {
  return `${PRESET_PREFIX}${id}`;
}

export function presetUrl(id: string): string {
  return `/logos/${id}.png`;
}

export function defaultLogoKey(): string {
  return makePresetKey(DEFAULT_LOGO_PRESET_ID);
}
