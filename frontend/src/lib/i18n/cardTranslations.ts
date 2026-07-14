export const CARD_T: Record<string, string> = {
  card_invalid: "Удостоверение недействительно",
  membership_card: "Членский билет",
  membership_subtitle: "Член союза театральных деятелей",
  logo_alt: "СТД РФ — Союз театральных деятелей Российской Федерации",
  label_birth_date: "Дата рождения",
  label_region: "Регион",
  label_card_issue_date: "Дата выдачи билета",
  label_join_date: "Член СТД с",
  label_chairman: "Председатель союза театральных деятелей Российской Федерации",
  label_email: "Email",
  label_phone: "Телефон",
  label_whatsapp: "WhatsApp",
  label_telegram: "Telegram",
  label_website: "Сайт",
  contact_btn: "Связаться с СТД",
  contact_title: "Связаться с нами",
  contact_close: "Закрыть",
};

function hexToRgb(hex: string): [number, number, number] {
  let v = hex.replace("#", "");
  if (v.length === 3) v = v.split("").map((c) => c + c).join("");
  if (v.length !== 6) return [31, 30, 94];
  return [
    parseInt(v.slice(0, 2), 16),
    parseInt(v.slice(2, 4), 16),
    parseInt(v.slice(4, 6), 16),
  ];
}

export function isLightColor(hex: string): boolean {
  const [r, g, b] = hexToRgb(hex);
  return (0.299 * r + 0.587 * g + 0.114 * b) / 255 > 0.55;
}

export interface CardPalette {
  text: string;
  textMuted: string;
  placeholderBg: string;
  placeholderStroke: string;
  logoSrc: string;
}

export function cardPalette(bgHex: string): CardPalette {
  const light = isLightColor(bgHex);
  if (light) {
    return {
      text: "#020617",
      textMuted: "rgba(2,6,23,0.65)",
      placeholderBg: "rgba(2,6,23,0.08)",
      placeholderStroke: "rgba(2,6,23,0.45)",
      logoSrc: "/std-logo-full-dark.png",
    };
  }
  return {
    text: "#FFFFFF",
    textMuted: "rgba(255,255,255,0.75)",
    placeholderBg: "rgba(255,255,255,0.15)",
    placeholderStroke: "rgba(255,255,255,0.6)",
    logoSrc: "/std-logo-full.png",
  };
}

export function formatDate(iso: string | undefined): string {
  if (!iso) return "—";
  try {
    return new Date(iso).toLocaleDateString("ru-RU");
  } catch {
    return iso;
  }
}
