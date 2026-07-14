import { describe, expect, it } from "vitest";
import {
  DEFAULT_LOGO_PRESET_ID,
  LOGO_PRESETS,
  defaultLogoKey,
  isPresetKey,
  makePresetKey,
  presetIdFromKey,
  presetUrl,
} from "../logoPresets";

describe("logoPresets", () => {
  it("exposes СТД as the default preset", () => {
    expect(DEFAULT_LOGO_PRESET_ID).toBe("std");
    expect(LOGO_PRESETS.find((p) => p.id === "std")?.name).toBe("СТД РФ");
  });

  it("identifies preset keys", () => {
    expect(isPresetKey("preset:std")).toBe(true);
    expect(isPresetKey("preset:foo")).toBe(true);
    expect(isPresetKey("cards/abc/logo-x.webp")).toBe(false);
    expect(isPresetKey(null)).toBe(false);
    expect(isPresetKey(undefined)).toBe(false);
    expect(isPresetKey("")).toBe(false);
  });

  it("extracts preset id", () => {
    expect(presetIdFromKey("preset:std")).toBe("std");
    expect(presetIdFromKey("preset:foo-bar")).toBe("foo-bar");
  });

  it("builds preset key", () => {
    expect(makePresetKey("std")).toBe("preset:std");
  });

  it("builds preset URL", () => {
    expect(presetUrl("std")).toBe("/logos/std.png");
  });

  it("defaultLogoKey is preset:std", () => {
    expect(defaultLogoKey()).toBe("preset:std");
  });
});
