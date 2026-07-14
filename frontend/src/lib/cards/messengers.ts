export const MESSENGER_TYPES = [
  "telegram", "whatsapp", "instagram", "facebook", "twitter", "youtube", "tiktok",
  "snapchat", "twitch", "discord", "linkedin", "vk", "ok", "max", "dribbble", "behance",
  "pinterest", "reddit", "spotify", "skype", "messenger", "patreon", "medium",
] as const;

export type MessengerType = (typeof MESSENGER_TYPES)[number];

export function isMessengerType(type: string): type is MessengerType {
  return (MESSENGER_TYPES as readonly string[]).includes(type);
}

const LABELS: Record<MessengerType, string> = {
  telegram: "Telegram", whatsapp: "WhatsApp", instagram: "Instagram",
  facebook: "Facebook", twitter: "X", youtube: "YouTube", tiktok: "TikTok",
  snapchat: "Snapchat", twitch: "Twitch", discord: "Discord", linkedin: "LinkedIn",
  vk: "ВКонтакте", ok: "Одноклассники", max: "MAX", dribbble: "Dribbble",
  behance: "Behance", pinterest: "Pinterest", reddit: "Reddit", spotify: "Spotify",
  skype: "Skype", messenger: "Messenger", patreon: "Patreon", medium: "Medium",
};

export function messengerLabel(type: string): string {
  if (isMessengerType(type)) return LABELS[type];
  return type.charAt(0).toUpperCase() + type.slice(1);
}

export function messengerHref(type: string, value: string): string {
  const v = (value || "").trim();
  if (v.startsWith("https://") || v.startsWith("http://")) return v;
  const stripAt = (s: string) => s.replace(/^@/, "");
  const enc = (s: string) => encodeURIComponent(s);
  const waPhone = (s: string) => {
    const digits = s.replace(/\D/g, "");
    return digits.length === 11 && digits.startsWith("8") ? `7${digits.slice(1)}` : digits;
  };
  switch (type) {
    case "telegram": return `https://t.me/${enc(stripAt(v))}`;
    case "whatsapp": return `https://wa.me/${waPhone(v)}`;
    case "instagram": return `https://instagram.com/${enc(stripAt(v))}`;
    case "facebook": return `https://facebook.com/${enc(v)}`;
    case "twitter": return `https://x.com/${enc(stripAt(v))}`;
    case "youtube": return `https://youtube.com/${enc(v)}`;
    case "tiktok": return `https://tiktok.com/@${enc(stripAt(v))}`;
    case "snapchat": return `https://snapchat.com/add/${enc(stripAt(v))}`;
    case "twitch": return `https://twitch.tv/${enc(stripAt(v))}`;
    case "discord": return `https://discord.com/users/${enc(stripAt(v))}`;
    case "linkedin": return `https://linkedin.com/in/${enc(v)}`;
    case "vk": return `https://vk.com/${enc(v)}`;
    case "ok": return `https://ok.ru/${enc(v)}`;
    case "max": return `https://max.ru/${enc(stripAt(v))}`;
    case "dribbble": return `https://dribbble.com/${enc(stripAt(v))}`;
    case "behance": return `https://behance.net/${enc(stripAt(v))}`;
    case "pinterest": return `https://pinterest.com/${enc(stripAt(v))}`;
    case "reddit": return `https://reddit.com/user/${enc(v.replace(/^u\//, "").replace(/^@/, ""))}`;
    case "spotify": return `https://open.spotify.com/user/${enc(v)}`;
    case "skype": return `skype:${v}?chat`;
    case "messenger": return `https://m.me/${enc(stripAt(v))}`;
    case "patreon": return `https://patreon.com/${enc(stripAt(v))}`;
    case "medium": return `https://medium.com/@${enc(stripAt(v))}`;
    default: return v;
  }
}

export function shortValue(value: string): string {
  let b = (value || "").trim();
  if (b.startsWith("https://")) b = b.slice(8);
  else if (b.startsWith("http://")) b = b.slice(7);
  if (b.startsWith("www.")) b = b.slice(4);
  if (b.endsWith("/")) b = b.slice(0, -1);
  if (b.length > 30) return `${b.slice(0, 18)}…${b.slice(-8)}`;
  return b;
}
