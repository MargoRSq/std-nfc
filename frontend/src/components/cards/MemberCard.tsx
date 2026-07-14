import { useState } from "react";
import type { CustomField } from "@/components/cards/CustomFieldsEditor";
import { CARD_T, formatDate } from "@/lib/i18n/cardTranslations";
import {
  isMessengerType,
  messengerHref,
  messengerLabel,
  shortValue,
} from "@/lib/cards/messengers";
import { isPresetKey, presetIdFromKey, presetUrl } from "@/lib/logoPresets";
import { formatPhoneRu } from "@/lib/cards/formatPhone";
import { buildFieldRenderOrder, type PresetKey } from "@/components/cards/cardFields";

function logoSrc(key: string): string {
  if (isPresetKey(key)) return presetUrl(presetIdFromKey(key));
  return `/api/media/${key}`;
}

interface ContactBlock {
  type: string | null;
  value: string;
  label?: string | null;
  is_hidden?: boolean;
}

interface AvatarGradient {
  from: string;
  to: string;
  angle?: number;
}

interface CardPreviewData {
  last_name?: string;
  first_name?: string;
  middle_name?: string;
  membership_no?: string;
  birth_date?: string;
  region?: string;
  chairman?: string;
  card_issue_date?: string;
  join_date?: string;
  bg_kind?: "solid" | "gradient";
  bg_color?: string;
  bg_gradient?: { from: string; to: string; angle: number };
  photo_shape?: "square" | "circle";
  photo_key?: string | null;
  logo_key?: string | null;
  logo_shape?: "square" | "circle" | "rectangle";
  feedback_form_enabled?: boolean;
  label_set?: CustomField[];
  field_order?: string[];
  contacts?: ContactBlock[];
  internal_blocks?: ContactBlock[];
  avatar_color?: string;
  avatar_gradient?: AvatarGradient;
  hide_birth_date?: boolean;
  hide_region?: boolean;
  hide_card_issue_date?: boolean;
  hide_join_date?: boolean;
  hide_chairman?: boolean;
}

interface Props {
  data: CardPreviewData;
}

const BRAND_NAVY = "#1F1E5E";
const FALLBACK_BG = "#1F1E5E";

function bgSolidOf(data: CardPreviewData): string {
  if (data.bg_kind === "gradient" && data.bg_gradient) {
    return data.bg_gradient.from ?? FALLBACK_BG;
  }
  return data.bg_color || FALLBACK_BG;
}

function headerBg(data: CardPreviewData): string {
  if (data.bg_kind === "gradient" && data.bg_gradient) {
    const { from, to } = data.bg_gradient;
    return `linear-gradient(180deg, ${from} 0%, ${to} 100%)`;
  }
  return data.bg_color || FALLBACK_BG;
}

function avatarBgStyle(data: CardPreviewData): React.CSSProperties {
  if (data.avatar_gradient && data.avatar_gradient.from && data.avatar_gradient.to) {
    const angle = data.avatar_gradient.angle ?? 135;
    return {
      background: `linear-gradient(${angle}deg, ${data.avatar_gradient.from}, ${data.avatar_gradient.to})`,
    };
  }
  if (data.avatar_color) return { background: data.avatar_color };
  return {};
}

function logoShapeClass(shape: "square" | "circle" | "rectangle"): string {
  if (shape === "circle") return "h-14 w-14 rounded-full";
  if (shape === "rectangle") return "h-14 w-auto min-w-[56px] max-w-[168px] rounded-[8px]";
  return "h-14 w-14 rounded-[8px]";
}

function plainLabelFor(type: string, t: Record<string, string>): string {
  if (type === "email") return t.label_email;
  if (type === "notes") return t.label_notes ?? "Заметки";
  return type;
}

function FieldRow({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div className="flex flex-col gap-[6px]">
      <span className="pl-1 text-[14px] font-medium" style={{ color: BRAND_NAVY }}>
        {label}:
      </span>
      <div className="rounded-[12px] border border-std-border bg-white px-4 py-[14px] shadow-[0_1px_2px_rgba(0,0,0,0.04)]">
        <span
          className="text-[16px] font-semibold break-words"
          style={{ color: BRAND_NAVY }}
        >
          {value}
        </span>
      </div>
    </div>
  );
}

function MessengerPill({ block }: { block: ContactBlock }) {
  const label = block.label?.trim() || (block.type ? messengerLabel(block.type) : "Контакт");
  const href = block.type ? messengerHref(block.type, block.value) : block.value;
  return (
    <a
      className="flex flex-row items-center gap-3 rounded-[12px] border border-std-border bg-white px-4 py-[14px] no-underline shadow-[0_1px_2px_rgba(0,0,0,0.04)]"
      href={href}
      target="_blank"
      rel="noopener noreferrer"
      style={{ color: "inherit" }}
    >
      <span className="flex h-9 w-9 flex-shrink-0 items-center justify-center rounded-[10px] bg-std-surface-3 text-std-primary">
        <span className="text-[14px] font-semibold">{label.charAt(0)}</span>
      </span>
      <span className="flex min-w-0 flex-1 flex-col gap-[2px]">
        <span className="text-[14px] font-medium" style={{ color: BRAND_NAVY }}>
          {label}
        </span>
        <span
          className="text-[16px] font-semibold break-all"
          style={{ color: BRAND_NAVY }}
        >
          {shortValue(block.value)}
        </span>
      </span>
    </a>
  );
}

export function MemberCard({ data }: Props) {
  const [modalOpen, setModalOpen] = useState(false);
  const t = CARD_T;

  const solidBg = bgSolidOf(data);
  const cardHeaderBg = headerBg(data);

  const fullName =
    [data.last_name, data.first_name, data.middle_name].filter(Boolean).join(" ").trim() ||
    "ФИО участника";
  const initials = `${(data.last_name || "").charAt(0).toUpperCase()}${(data.first_name || "").charAt(0).toUpperCase()}`;

  const logoShape = data.logo_shape ?? "square";

  const visibleContacts = (data.contacts ?? []).filter(
    (c) => c.value && !c.is_hidden && c.type !== "phone",
  );
  const labelSet: CustomField[] = data.label_set ?? [];

  const renderPreset = (key: PresetKey): React.ReactNode => {
    switch (key) {
      case "birth_date":
        if (!data.birth_date || data.hide_birth_date) return null;
        return (
          <FieldRow
            key="birth_date"
            label={t.label_birth_date}
            value={formatDate(data.birth_date)}
          />
        );
      case "region":
        if (!data.region || data.hide_region) return null;
        return <FieldRow key="region" label={t.label_region} value={data.region} />;
      case "card_issue_date":
        if (!data.card_issue_date || data.hide_card_issue_date) return null;
        return (
          <FieldRow
            key="card_issue_date"
            label={t.label_card_issue_date}
            value={formatDate(data.card_issue_date)}
          />
        );
      case "join_date": {
        if (!data.join_date || data.hide_join_date) return null;
        const year = (() => {
          try {
            return new Date(data.join_date).getFullYear();
          } catch {
            return data.join_date;
          }
        })();
        return <FieldRow key="join_date" label={t.label_join_date} value={`с ${year}`} />;
      }
      case "chairman":
        if (!data.chairman || data.hide_chairman) return null;
        return <FieldRow key="chairman" label={t.label_chairman} value={data.chairman} />;
    }
  };

  return (
    <div
      className="flex w-full flex-col items-center gap-6 pt-6"
      style={{
        background: solidBg,
        fontFamily: "Manrope, -apple-system, BlinkMacSystemFont, sans-serif",
        minHeight: "100%",
      }}
    >
      <div className="flex w-full justify-center">
        <div className="flex w-full max-w-[380px] flex-col overflow-hidden">
          <div
            className="flex flex-col items-center gap-5 px-4 pb-5 pt-4 text-center text-white"
            style={{ background: cardHeaderBg }}
          >
            <div className="flex min-h-12 w-full items-center justify-center">
              {data.logo_key ? (
                <div
                  className={`inline-flex items-center justify-center overflow-hidden bg-white p-[6px] ${logoShapeClass(logoShape)}`}
                >
                  <img
                    src={logoSrc(data.logo_key)}
                    alt={t.logo_alt}
                    className="h-full w-auto max-w-full object-contain"
                  />
                </div>
              ) : (
                <div className="inline-flex h-14 items-center justify-center overflow-hidden rounded-[8px] bg-white px-3 py-[6px]">
                  <img
                    src="/std-logo-full.png"
                    alt={t.logo_alt}
                    className="h-full w-auto object-contain"
                  />
                </div>
              )}
            </div>
            <div className="text-[22px] font-semibold leading-[1.15] tracking-[-0.01em] text-white">
              {t.membership_card} №{data.membership_no || "_______"}
            </div>
          </div>

          <div
            className="relative w-full overflow-hidden"
            style={{ aspectRatio: "31 / 34", background: "rgba(255,255,255,0.15)" }}
          >
            {data.photo_key ? (
              <img
                src={`/api/media/${data.photo_key}`}
                alt={fullName}
                className="absolute inset-0 block h-full w-full object-cover"
              />
            ) : (
              <div
                className="absolute inset-0 flex h-full w-full items-center justify-center"
                style={{ background: "rgba(255,255,255,0.15)", ...avatarBgStyle(data) }}
              >
                <span className="text-[120px] font-medium leading-none tracking-[0.0235em] text-white">
                  {initials || "ИИ"}
                </span>
              </div>
            )}
            <div
              className="absolute inset-x-0 bottom-0 flex flex-col items-center gap-1 px-5 pb-[22px] pt-[18px] text-center text-white"
              style={{
                background:
                  "linear-gradient(180deg, rgba(0,0,0,0) 0%, rgba(0,0,0,0.55) 100%)",
              }}
            >
              <div
                className="text-[22px] font-bold leading-[1.25] text-white"
                style={{ textShadow: "0 2px 8px rgba(0,0,0,0.35)" }}
              >
                {fullName}
              </div>
              <div
                className="text-[14px] font-medium leading-[1.3]"
                style={{
                  color: "rgba(255,255,255,0.92)",
                  textShadow: "0 2px 8px rgba(0,0,0,0.35)",
                }}
              >
                {t.membership_subtitle}
              </div>
            </div>
          </div>

          <div className="flex flex-col gap-[14px] bg-white px-4 pb-6 pt-5">
            {buildFieldRenderOrder(data.field_order, labelSet).map((it, idx) =>
              it.kind === "preset" ? (
                renderPreset(it.key)
              ) : it.field.value && !it.field.is_hidden ? (
                <FieldRow
                  key={`label-${it.field.key}`}
                  label={it.field.label || `Поле ${idx + 1}`}
                  value={
                    it.field.type === "phone"
                      ? formatPhoneRu(it.field.value)
                      : it.field.type === "date"
                        ? formatDate(it.field.value)
                        : it.field.value
                  }
                />
              ) : null,
            )}
            {visibleContacts.map((c, idx) => {
              const customLabel = c.label?.trim();
              if (c.type && isMessengerType(c.type)) {
                return <MessengerPill key={`c-${idx}`} block={c} />;
              }
              const label = customLabel || (c.type ? plainLabelFor(c.type, t) : "Поле");
              return <FieldRow key={`c-${idx}`} label={label} value={c.value} />;
            })}

            {data.feedback_form_enabled && (
              <button
                type="button"
                onClick={() => setModalOpen(true)}
                className="mt-[6px] block w-full rounded-full px-6 py-[14px] text-center text-[15px] font-semibold text-white"
                style={{ background: solidBg, fontFamily: "inherit", border: 0, cursor: "pointer" }}
              >
                {t.contact_btn}
              </button>
            )}
          </div>
        </div>
      </div>

      {modalOpen && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center p-4"
          style={{ background: "rgba(0,0,0,0.5)" }}
          onClick={() => setModalOpen(false)}
        >
          <div
            className="relative flex w-full max-w-[360px] flex-col gap-4 rounded-[28px] bg-white p-6"
            onClick={(e) => e.stopPropagation()}
          >
            <p
              className="pr-12 text-[18px] font-semibold"
              style={{ color: "#020617" }}
            >
              {t.contact_title}
            </p>
            <a
              href="mailto:stdrf@stdrf.ru"
              className="flex flex-col gap-1 rounded-[12px] border border-std-border bg-white px-4 py-3 no-underline"
            >
              <span className="pl-1 text-[14px] font-medium" style={{ color: BRAND_NAVY }}>
                {t.label_email}
              </span>
              <span className="text-[16px] font-semibold" style={{ color: BRAND_NAVY }}>
                stdrf@stdrf.ru
              </span>
            </a>
            <a
              href="tel:+74956502846"
              className="flex flex-col gap-1 rounded-[12px] border border-std-border bg-white px-4 py-3 no-underline"
            >
              <span className="pl-1 text-[14px] font-medium" style={{ color: BRAND_NAVY }}>
                {t.label_phone}
              </span>
              <span className="text-[16px] font-semibold" style={{ color: BRAND_NAVY }}>
                +7(495)650-28-46
              </span>
            </a>
            <a
              href="https://stdrf.ru"
              target="_blank"
              rel="noopener"
              className="flex flex-col gap-1 rounded-[12px] border border-std-border bg-white px-4 py-3 no-underline"
            >
              <span className="pl-1 text-[14px] font-medium" style={{ color: BRAND_NAVY }}>
                {t.label_website}
              </span>
              <span className="text-[16px] font-semibold" style={{ color: BRAND_NAVY }}>
                stdrf.ru
              </span>
            </a>
            <button
              type="button"
              onClick={() => setModalOpen(false)}
              aria-label={t.contact_close}
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
