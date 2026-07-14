import type { ContactType } from "@/components/cards/ContactBlocksEditor";
import type { LabelPresetType } from "@/lib/api/labelPresets";

const NAME_MAP: Record<string, ContactType> = {
  "телефон": "phone",
  "phone": "phone",
  "tel": "phone",
  "email": "email",
  "почта": "email",
  "e-mail": "email",
  "сайт": "website",
  "website": "website",
  "url": "website",
  "telegram": "telegram",
  "телеграм": "telegram",
  "tg": "telegram",
  "whatsapp": "whatsapp",
  "ватсап": "whatsapp",
  "wa": "whatsapp",
  "max": "max",
  "макс": "max",
  "вконтакте": "vk",
  "vk": "vk",
  "vkontakte": "vk",
  "одноклассники": "ok",
  "ok": "ok",
  "ok.ru": "ok",
  "instagram": "instagram",
  "инстаграм": "instagram",
  "инстаграмм": "instagram",
  "ig": "instagram",
  "facebook": "facebook",
  "фейсбук": "facebook",
  "fb": "facebook",
  "twitter": "twitter",
  "твиттер": "twitter",
  "x": "twitter",
  "youtube": "youtube",
  "ютуб": "youtube",
  "yt": "youtube",
  "tiktok": "tiktok",
  "тикток": "tiktok",
  "snapchat": "snapchat",
  "снэпчат": "snapchat",
  "twitch": "twitch",
  "twitch.tv": "twitch",
  "discord": "discord",
  "дискорд": "discord",
  "linkedin": "linkedin",
  "линкедин": "linkedin",
};

export function contactTypeFromPreset(
  label: string,
  presetType: LabelPresetType,
): ContactType | null {
  const norm = label.trim().toLowerCase();
  const byName = NAME_MAP[norm];
  if (byName) return byName;
  if (presetType === "phone") return "phone";
  if (presetType === "email") return "email";
  if (presetType === "url") return "website";
  return null;
}
