import { useState } from "react";
import type {
  BackgroundGradient,
  CardCreateRequest,
  ContactBlock,
  CustomField,
} from "@/lib/api/cards";
import { formatDateRu, yearOf } from "@/lib/cards/format";
import { formatPhoneRu } from "@/lib/cards/formatPhone";
import { buildFieldRenderOrder } from "@/components/cards/cardFields";
import { CARD_T } from "@/lib/i18n/cardTranslations";
import {
  isMessengerType,
  messengerHref,
  messengerLabel,
  shortValue,
} from "@/lib/cards/messengers";

type CardT = typeof CARD_T;

interface Props {
  payload: CardCreateRequest & { photo_key?: string | null };
  pendingLogoUrl?: string | null;
  pendingPhotoUrl?: string | null;
}

const PRESET_KEYS = ["birth_date", "region", "card_issue_date", "join_date", "chairman"] as const;
type PresetKey = (typeof PRESET_KEYS)[number];

const FALLBACK_BG = "#1F1E5E";
const BRAND_NAVY = "#1F1E5E";

function gradientCss(g: BackgroundGradient, mode: "card" | "avatar"): string {
  if (mode === "card") {
    const from = (g as unknown as { start?: string; from?: string }).start ?? g.from ?? "#1F1E5E";
    const to = (g as unknown as { end?: string; to?: string }).end ?? g.to ?? "#798BFF";
    return `linear-gradient(180deg, ${from} 0%, ${to} 100%)`;
  }
  return `linear-gradient(${g.angle ?? 135}deg, ${g.from}, ${g.to})`;
}

function headerBg(payload: CardCreateRequest): string {
  if (payload.bg_kind === "gradient" && payload.bg_gradient) {
    return gradientCss(payload.bg_gradient, "card");
  }
  return payload.bg_color || FALLBACK_BG;
}

function avatarBgStyle(payload: CardCreateRequest): React.CSSProperties {
  if (payload.avatar_gradient && payload.avatar_gradient.from && payload.avatar_gradient.to) {
    return { background: gradientCss(payload.avatar_gradient, "avatar") };
  }
  if (payload.avatar_color) return { background: payload.avatar_color };
  return {};
}

function logoUrl(logoKey: string | null | undefined): { src: string } | null {
  if (!logoKey) return null;
  if (logoKey.startsWith("preset:")) {
    return { src: `/logos/${logoKey.slice(7)}.png` };
  }
  return { src: `/api/media/${logoKey}` };
}

function MessengerIcon({ type }: { type: string }) {
  const cls = "w-5 h-5";
  const stroke = { stroke: "currentColor", strokeWidth: 2, strokeLinecap: "round" as const, strokeLinejoin: "round" as const, fill: "none" };
  switch (type) {
    case "telegram":
      return <img className={cls} src="/messengers/telegram.svg" alt="Telegram" />;
    case "max":
      return <img className={cls} src="/messengers/max.svg" alt="MAX" />;
    case "whatsapp":
    case "skype":
    case "messenger":
      return (
        <svg className={cls} viewBox="0 0 24 24" {...stroke}>
          <path d="M2.992 16.342a2 2 0 0 1 .094 1.167l-1.065 3.29a1 1 0 0 0 1.236 1.168l3.413-.998a2 2 0 0 1 1.099.092 10 10 0 1 0-4.777-4.719" />
        </svg>
      );
    case "instagram":
      return (
        <svg className={cls} viewBox="0 0 24 24" {...stroke}>
          <rect width="20" height="20" x="2" y="2" rx="5" ry="5" />
          <path d="M16 11.37A4 4 0 1 1 12.63 8 4 4 0 0 1 16 11.37z" />
          <line x1="17.5" x2="17.51" y1="6.5" y2="6.5" />
        </svg>
      );
    case "facebook":
      return (
        <svg className={cls} viewBox="0 0 24 24" {...stroke}>
          <path d="M18 2h-3a5 5 0 0 0-5 5v3H7v4h3v8h4v-8h3l1-4h-4V7a1 1 0 0 1 1-1h3z" />
        </svg>
      );
    case "twitter":
      return (
        <svg className={cls} viewBox="0 0 24 24" {...stroke}>
          <path d="M22 4s-.7 2.1-2 3.4c1.6 10-9.4 17.3-18 11.6 2.2.1 4.4-.6 6-2C3 15.5.5 9.6 3 5c2.2 2.6 5.6 4.1 9 4-.9-4.2 4-6.6 7-3.8 1.1 0 3-1.2 3-1.2z" />
        </svg>
      );
    case "youtube":
      return (
        <svg className={cls} viewBox="0 0 24 24" {...stroke}>
          <path d="M2.5 17a24.12 24.12 0 0 1 0-10 2 2 0 0 1 1.4-1.4 49.56 49.56 0 0 1 16.2 0A2 2 0 0 1 21.5 7a24.12 24.12 0 0 1 0 10 2 2 0 0 1-1.4 1.4 49.55 49.55 0 0 1-16.2 0A2 2 0 0 1 2.5 17" />
          <path d="m10 15 5-3-5-3z" />
        </svg>
      );
    case "tiktok":
    case "spotify":
      return (
        <svg className={cls} viewBox="0 0 24 24" {...stroke}>
          <path d="M9 18V5l12-2v13" />
          <circle cx="6" cy="18" r="3" />
          <circle cx="18" cy="16" r="3" />
        </svg>
      );
    case "linkedin":
      return (
        <svg className={cls} viewBox="0 0 24 24" {...stroke}>
          <path d="M16 8a6 6 0 0 1 6 6v7h-4v-7a2 2 0 0 0-2-2 2 2 0 0 0-2 2v7h-4v-7a6 6 0 0 1 6-6z" />
          <rect width="4" height="12" x="2" y="9" />
          <circle cx="4" cy="4" r="2" />
        </svg>
      );
    case "vk":
      return (
        <svg className={cls} viewBox="0 0 24 24" {...stroke}>
          <rect x="2" y="3" width="20" height="18" rx="4" />
          <path d="M7 9l3 6 2-4 2 4 3-6" />
        </svg>
      );
    case "ok":
      return (
        <svg className={cls} viewBox="0 0 24 24" {...stroke}>
          <circle cx="12" cy="7" r="4" />
          <path d="M6 14c2 2 4 3 6 3s4-1 6-3" />
          <path d="M9 21l3-4 3 4" />
        </svg>
      );
    default:
      return (
        <svg className={cls} viewBox="0 0 24 24" {...stroke}>
          <circle cx="12" cy="12" r="4" />
          <path d="M16 8v5a3 3 0 0 0 6 0v-1a10 10 0 1 0-4 8" />
        </svg>
      );
  }
}

function PhoneIcon() {
  return (
    <svg className="w-5 h-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round">
      <path d="M22 16.92v3a2 2 0 0 1-2.18 2 19.79 19.79 0 0 1-8.63-3.07 19.5 19.5 0 0 1-6-6 19.79 19.79 0 0 1-3.07-8.67A2 2 0 0 1 4.11 2h3a2 2 0 0 1 2 1.72 12.84 12.84 0 0 0 .7 2.81 2 2 0 0 1-.45 2.11L8.09 9.91a16 16 0 0 0 6 6l1.27-1.27a2 2 0 0 1 2.11-.45 12.84 12.84 0 0 0 2.81.7A2 2 0 0 1 22 16.92z" />
    </svg>
  );
}

function PillRow({ children }: { children: React.ReactNode }) {
  return <div className="min-w-0">{children}</div>;
}

function plainLabelFor(type: string): string {
  switch (type) {
    case "email": return "Email";
    case "phone": return "Телефон";
    case "website": return "Сайт";
    case "fax": return "Факс";
    case "notes": return "Заметки";
    default: return type;
  }
}

function MessengerPill({ block }: { block: ContactBlock }) {
  const label = block.label?.trim() || (block.type ? messengerLabel(block.type) : "Контакт");
  const href = block.type ? messengerHref(block.type, block.value) : block.value;
  return (
    <a
      className="flex flex-row items-center gap-3 rounded-[12px] border border-std-border bg-white px-3 py-[10px] no-underline shadow-std-sm"
      href={href}
      target="_blank"
      rel="noopener noreferrer"
      style={{ color: "inherit" }}
    >
      <span className="flex h-9 w-9 flex-shrink-0 items-center justify-center rounded-full bg-std-surface-3 text-std-primary">
        <MessengerIcon type={block.type ?? ""} />
      </span>
      <span className="flex min-w-0 flex-1 flex-col">
        <span className="text-sm font-medium leading-[18px]" style={{ color: "#727272" }}>
          {label}:
        </span>
        <span className="text-[18px] font-medium break-all leading-[22px]" style={{ color: BRAND_NAVY }}>
          {shortValue(block.value)}
        </span>
      </span>
    </a>
  );
}

function FieldRow({ label, value, icon }: { label: React.ReactNode; value: React.ReactNode; icon?: React.ReactNode }) {
  return (
    <div className="flex flex-row items-center gap-3 rounded-[12px] border border-std-border bg-white px-3 py-[10px] shadow-std-sm">
      {icon ? (
        <span className="flex h-9 w-9 flex-shrink-0 items-center justify-center rounded-full bg-std-surface-3 text-std-primary">
          {icon}
        </span>
      ) : null}
      <div className="flex min-w-0 flex-1 flex-col">
        <span className="text-sm font-medium leading-[18px]" style={{ color: "#727272" }}>
          {label}:
        </span>
        <span className="text-[18px] font-medium break-words leading-[22px]" style={{ color: BRAND_NAVY }}>
          {value}
        </span>
      </div>
    </div>
  );
}

function isVisiblePreset(field: PresetKey, payload: CardCreateRequest): boolean {
  switch (field) {
    case "birth_date":
      return !!payload.birth_date && !payload.hide_birth_date;
    case "region":
      return !!payload.region && !payload.hide_region;
    case "card_issue_date":
      return !!payload.card_issue_date && !payload.hide_card_issue_date;
    case "join_date":
      return !!payload.join_date && !payload.hide_join_date;
    case "chairman":
      return false;
  }
}

const PRESET_LABEL_KEY: Record<PresetKey, string> = {
  birth_date: "label_birth_date",
  region: "label_region",
  card_issue_date: "label_card_issue_date",
  join_date: "label_join_date",
  chairman: "label_chairman",
};

function presetLabel(
  key: PresetKey,
  t: CardT,
  fieldLabels: Record<string, string> | undefined,
): string {
  const override = fieldLabels?.[key];
  if (override && override.trim()) return override;
  return t[PRESET_LABEL_KEY[key]];
}

function PresetField({
  field,
  payload,
  t,
}: {
  field: PresetKey;
  payload: CardCreateRequest;
  t: CardT;
}) {
  const label = presetLabel(field, t, payload.field_labels);
  switch (field) {
    case "birth_date":
      if (!payload.birth_date || payload.hide_birth_date) return null;
      return <FieldRow label={label} value={formatDateRu(payload.birth_date)} />;
    case "region":
      if (!payload.region || payload.hide_region) return null;
      return <FieldRow label={label} value={payload.region} />;
    case "card_issue_date":
      if (!payload.card_issue_date || payload.hide_card_issue_date) return null;
      return <FieldRow label={label} value={formatDateRu(payload.card_issue_date)} />;
    case "join_date":
      if (!payload.join_date || payload.hide_join_date) return null;
      return <FieldRow label={label} value={`с ${yearOf(payload.join_date)}`} />;
    case "chairman":
      return null;
  }
}

function ContactItem({ block }: { block: ContactBlock }) {
  if (!block.value) return null;
  if (block.type && isMessengerType(block.type)) return <MessengerPill block={block} />;
  const icon = block.type === "phone" ? <PhoneIcon /> : undefined;
  const label = block.label?.trim() || (block.type ? plainLabelFor(block.type) : "Поле");
  const value = block.type === "phone" ? formatPhoneRu(block.value) : block.value;
  return <FieldRow label={label} value={value} icon={icon} />;
}

const LABEL_NAME_TO_MESSENGER: Record<string, string> = {
  telegram: "telegram", телеграм: "telegram", tg: "telegram",
  whatsapp: "whatsapp", ватсап: "whatsapp", wa: "whatsapp",
  max: "max", макс: "max",
  вконтакте: "vk", vk: "vk",
  одноклассники: "ok", ok: "ok",
  instagram: "instagram", инстаграм: "instagram", инстаграмм: "instagram",
  facebook: "facebook", фейсбук: "facebook",
  twitter: "twitter", твиттер: "twitter", x: "twitter",
  youtube: "youtube", ютуб: "youtube",
  tiktok: "tiktok", тикток: "tiktok",
  snapchat: "snapchat", twitch: "twitch", discord: "discord",
  linkedin: "linkedin", линкедин: "linkedin",
};

function iconForLabel(label: string): React.ReactNode | undefined {
  const norm = (label || "").trim().toLowerCase();
  if (norm === "телефон" || norm === "phone" || norm === "tel") return <PhoneIcon />;
  const mess = LABEL_NAME_TO_MESSENGER[norm];
  if (mess) return <MessengerIcon type={mess} />;
  return undefined;
}

export function MemberCardPreview({ payload, pendingLogoUrl, pendingPhotoUrl }: Props) {
  const t = CARD_T;
  const [contactOpen, setContactOpen] = useState(false);
  const fullName = [payload.last_name, payload.first_name, payload.middle_name].filter(Boolean).join(" ").trim();
  const logoShape = payload.logo_shape ?? "square";
  const photoShape = payload.photo_shape ?? "circle";
  const logo = pendingLogoUrl ? { src: pendingLogoUrl } : logoUrl(payload.logo_key);
  const initials = `${(payload.last_name || "").charAt(0).toUpperCase()}${(payload.first_name || "").charAt(0).toUpperCase()}`;

  const rawOrder = (payload.field_order ?? []).filter((k): k is PresetKey =>
    (PRESET_KEYS as readonly string[]).includes(k),
  );
  const missing = (PRESET_KEYS as readonly PresetKey[]).filter((k) => !rawOrder.includes(k));
  const ordered: PresetKey[] = [...rawOrder, ...missing];

  // Parity with MemberCard.tsx:169-171 — same predicate so preview matches published card.
  const visibleContacts = (payload.contacts ?? []).filter((c) => c.value && !c.is_hidden && c.type !== "phone");
  const labelSet: CustomField[] = payload.label_set ?? [];

  const avatarShapeCls = photoShape === "circle" ? "rounded-full" : "rounded-[16px]";
  const renderOrder = buildFieldRenderOrder(payload.field_order, labelSet).filter(
    (it) => !(it.kind === "preset" && it.key === "chairman"),
  );
  const showChairman = ordered.includes("chairman") && !!payload.chairman && !payload.hide_chairman;
  const hasServiceSection = showChairman || visibleContacts.length > 0;

  const logoShapeCls =
    logoShape === "circle"
      ? "w-14 h-14 rounded-full"
      : logoShape === "rectangle"
      ? "h-14 max-w-[168px] min-w-[56px] rounded-[8px] w-auto"
      : "w-14 h-14 rounded-[8px]";

  return (
    <div
      className="flex w-full flex-col overflow-hidden rounded-[24px]"
      style={{
        fontFamily: "Manrope, -apple-system, BlinkMacSystemFont, sans-serif",
        background: headerBg(payload),
        color: "#FFFFFF",
      }}
    >
      <div className="flex flex-col items-center gap-4 px-4 pt-5 text-center">
        <div className="flex min-h-12 w-full items-center justify-center">
          {logo ? (
            <div className={`inline-flex items-center justify-center overflow-hidden bg-white p-[6px] ${logoShapeCls}`}>
              <img src={logo.src} alt="Логотип" className="h-full w-auto max-w-full object-contain" />
            </div>
          ) : (
            <div className="inline-flex h-14 items-center justify-center overflow-hidden rounded-[8px] bg-white px-3 py-[6px]">
              <img src="/std-logo-full.png" alt="Логотип" className="h-full w-auto object-contain" />
            </div>
          )}
        </div>

        <div className="text-[17px] font-semibold leading-[1.2] tracking-[-0.01em] text-white">
          {t.membership_card} №{payload.membership_no || " "}
        </div>

        <div className="pt-2">
          {payload.photo_key || pendingPhotoUrl ? (
            <div
              className={`overflow-hidden ${avatarShapeCls}`}
              style={{ width: 140, height: 140 }}
            >
              <img
                src={pendingPhotoUrl || `/api/media/${payload.photo_key}`}
                alt="Фото"
                className="h-full w-full object-cover"
              />
            </div>
          ) : (
            <div
              className={`flex items-center justify-center ${avatarShapeCls}`}
              style={{
                width: 140,
                height: 140,
                background: "rgba(255,255,255,0.15)",
                ...avatarBgStyle(payload),
              }}
            >
              <span className="text-[56px] font-medium leading-none tracking-[0.02em] text-white">
                {initials || "ИИ"}
              </span>
            </div>
          )}
        </div>

        <div className="text-[18px] font-semibold leading-[1.2] text-white">
          {fullName || "Иванов Иван Иванович"}
        </div>
      </div>

      <div className="flex flex-col gap-[10px] px-4 pt-5 pb-2">
        {renderOrder.map((it) => {
          if (it.kind === "preset") {
            if (!isVisiblePreset(it.key, payload)) return null;
            return (
              <PillRow key={`p-${it.key}`}>
                <PresetField field={it.key} payload={payload} t={t} />
              </PillRow>
            );
          }
          const f = it.field;
          if (!f.value || f.is_hidden) return null;
          return (
            <PillRow key={`c-${f.key}`}>
              <FieldRow
                label={f.label}
                value={
                  f.type === "phone"
                    ? formatPhoneRu(f.value)
                    : f.type === "date"
                      ? formatDateRu(f.value)
                      : f.value
                }
                icon={iconForLabel(f.label)}
              />
            </PillRow>
          );
        })}
      </div>

      {hasServiceSection && (
        <div className="flex flex-col gap-[10px] px-4 pt-5 pb-2">
          {visibleContacts.map((c) =>
            c.value ? (
              <PillRow key={`${c.type ?? ""}-${c.value}`}>
                <ContactItem block={c} />
              </PillRow>
            ) : null,
          )}
          {showChairman && (
            <PillRow>
              <FieldRow
                label={presetLabel("chairman", t, payload.field_labels)}
                value={payload.chairman}
              />
            </PillRow>
          )}
        </div>
      )}

      <div className="pt-3" />

      {payload.feedback_form_enabled === true ? (
        <div className="px-4 pb-5 pt-2">
          <button
            type="button"
            onClick={() => setContactOpen(true)}
            className="block w-full rounded-full px-6 py-[14px] text-center text-[15px] font-semibold"
            style={{ background: "#F5F5F5", color: BRAND_NAVY, border: 0, cursor: "pointer" }}
          >
            {t.contact_btn}
          </button>
        </div>
      ) : (
        <div className="pb-5" />
      )}

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
              {t.contact_title}
            </p>
            {visibleContacts.some((c) => c.value) ? (
              visibleContacts.map((c) => <ContactItem key={`modal-${c.type ?? ""}-${c.value}`} block={c} />)
            ) : (
              <>
                <a
                  href="mailto:stdrf@stdrf.ru"
                  className="flex flex-col gap-1 rounded-[12px] border border-std-border bg-white px-4 py-3 no-underline"
                >
                  <span className="pl-1 text-[14px] font-medium" style={{ color: BRAND_NAVY }}>{t.label_email}</span>
                  <span className="text-[16px] font-semibold" style={{ color: BRAND_NAVY }}>stdrf@stdrf.ru</span>
                </a>
                <a
                  href="tel:+74956502846"
                  className="flex flex-col gap-1 rounded-[12px] border border-std-border bg-white px-4 py-3 no-underline"
                >
                  <span className="pl-1 text-[14px] font-medium" style={{ color: BRAND_NAVY }}>{t.label_phone}</span>
                  <span className="text-[16px] font-semibold" style={{ color: BRAND_NAVY }}>+7(495)650-28-46</span>
                </a>
                <a
                  href="https://stdrf.ru"
                  target="_blank"
                  rel="noopener"
                  className="flex flex-col gap-1 rounded-[12px] border border-std-border bg-white px-4 py-3 no-underline"
                >
                  <span className="pl-1 text-[14px] font-medium" style={{ color: BRAND_NAVY }}>{t.label_website}</span>
                  <span className="text-[16px] font-semibold" style={{ color: BRAND_NAVY }}>stdrf.ru</span>
                </a>
              </>
            )}
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
