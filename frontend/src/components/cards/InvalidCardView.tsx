import { useState } from "react";
import { UserX } from "lucide-react";
import type { Card } from "@/lib/api/cards";

const FALLBACK_BG = "#1F1E5E";
const BRAND_NAVY = "#1F1E5E";

interface Props {
  card: Pick<Card, "logo_key" | "membership_no" | "bg_kind" | "bg_color" | "bg_gradient">;
  membershipLabel: string;
  invalidLabel: string;
  contactLabel: string;
  logoAlt: string;
  messageText?: string | null;
  messageImageUrl?: string | null;
}

function cardHeaderBg(card: Props["card"]): string {
  if (card.bg_kind === "gradient" && card.bg_gradient) {
    return `linear-gradient(180deg, ${card.bg_gradient.from} 0%, ${card.bg_gradient.to} 100%)`;
  }
  return card.bg_color || FALLBACK_BG;
}

function logoUrl(logoKey: string | null | undefined): string | null {
  if (!logoKey) return null;
  if (logoKey.startsWith("preset:")) return `/logos/${logoKey.slice(7)}.png`;
  return `/api/media/${logoKey}`;
}

export function InvalidCardView({
  card,
  membershipLabel,
  invalidLabel,
  contactLabel,
  logoAlt,
  messageText,
  messageImageUrl,
}: Props) {
  const logo = logoUrl(card.logo_key);
  const text = messageText?.trim() || invalidLabel;
  const [contactOpen, setContactOpen] = useState(false);
  return (
    <div
      className="flex w-full flex-col overflow-hidden rounded-[24px]"
      style={{
        fontFamily: "Manrope, -apple-system, BlinkMacSystemFont, sans-serif",
        background: cardHeaderBg(card),
        color: "#FFFFFF",
      }}
    >
      <div className="flex flex-col items-center gap-4 px-4 pt-5 text-center">
        <div className="flex min-h-12 w-full items-center justify-center">
          {logo ? (
            <div className="inline-flex h-14 items-center justify-center overflow-hidden rounded-[8px] bg-white p-[6px]">
              <img src={logo} alt={logoAlt} className="h-full w-auto max-w-full object-contain" />
            </div>
          ) : (
            <img src="/std-logo-full.png" alt={logoAlt} className="max-h-14 w-auto object-contain" />
          )}
        </div>

        <div className="text-[17px] font-semibold leading-[1.2] tracking-[-0.01em] text-white">
          {membershipLabel} №{card.membership_no || " "}
        </div>

        <div className="pt-2">
          <div
            className="flex items-center justify-center overflow-hidden rounded-[16px] bg-white"
            style={{ width: 140, height: 140 }}
          >
            {messageImageUrl ? (
              <img src={messageImageUrl} alt="" className="h-full w-full object-cover" />
            ) : (
              <UserX className="h-16 w-16" style={{ color: "#1F1E5E" }} strokeWidth={1.5} />
            )}
          </div>
        </div>

        <div className="pt-1 px-2 text-[16px] font-semibold leading-[1.25] text-white break-words">
          {text}
        </div>
      </div>

      <div className="px-4 pb-5 pt-5">
        <button
          type="button"
          onClick={() => setContactOpen(true)}
          className="block w-full rounded-full px-6 py-[14px] text-center text-[15px] font-semibold"
          style={{ background: "#F5F5F5", color: "#1F1E5E", border: 0, cursor: "pointer" }}
        >
          {contactLabel}
        </button>
      </div>

      {contactOpen && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center p-4"
          style={{ background: "rgba(0,0,0,0.5)" }}
          onClick={() => setContactOpen(false)}
        >
          <div
            className="relative flex w-full max-w-[360px] flex-col gap-4 rounded-[28px] bg-white p-6"
            onClick={(e) => e.stopPropagation()}
          >
            <p className="pr-12 text-[18px] font-semibold" style={{ color: "#020617" }}>
              Связаться с нами
            </p>
            <a
              href="mailto:stdrf@stdrf.ru"
              className="flex flex-col gap-1 rounded-[12px] border border-std-border bg-white px-4 py-3 no-underline"
            >
              <span className="pl-1 text-[14px] font-medium" style={{ color: BRAND_NAVY }}>Email</span>
              <span className="text-[16px] font-semibold" style={{ color: BRAND_NAVY }}>stdrf@stdrf.ru</span>
            </a>
            <a
              href="tel:+74956502846"
              className="flex flex-col gap-1 rounded-[12px] border border-std-border bg-white px-4 py-3 no-underline"
            >
              <span className="pl-1 text-[14px] font-medium" style={{ color: BRAND_NAVY }}>Телефон</span>
              <span className="text-[16px] font-semibold" style={{ color: BRAND_NAVY }}>+7(495)650-28-46</span>
            </a>
            <a
              href="https://stdrf.ru"
              target="_blank"
              rel="noopener"
              className="flex flex-col gap-1 rounded-[12px] border border-std-border bg-white px-4 py-3 no-underline"
            >
              <span className="pl-1 text-[14px] font-medium" style={{ color: BRAND_NAVY }}>Сайт</span>
              <span className="text-[16px] font-semibold" style={{ color: BRAND_NAVY }}>stdrf.ru</span>
            </a>
            <button
              type="button"
              onClick={() => setContactOpen(false)}
              aria-label="Закрыть"
              className="absolute right-4 top-4 flex h-10 w-10 cursor-pointer items-center justify-center rounded-full border border-std-border bg-white text-[20px] leading-none"
              style={{ color: "#727272" }}
            >
              ×
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
