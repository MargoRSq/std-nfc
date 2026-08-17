import { Link, useNavigate, useParams } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { ArrowLeft, Edit, Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { MemberCardPreview } from "@/components/cards/MemberCardPreview";
import { InvalidCardView } from "@/components/cards/InvalidCardView";
import { cardsApi } from "@/lib/api/cards";
import { cardMessagesApi } from "@/lib/api/cardMessages";
import type { Card, CardCreateRequest } from "@/lib/api/cards";
import { CARD_T, formatDate } from "@/lib/i18n/cardTranslations";
import { messengerLabel } from "@/lib/cards/messengers";
import { useAuthStore } from "@/stores/authStore";

function cardToPayload(card: Card): CardCreateRequest & { photo_key?: string | null } {
  return {
    last_name: card.last_name,
    first_name: card.first_name,
    middle_name: card.middle_name ?? undefined,
    membership_no: card.membership_no,
    category_id: card.category_id,
    birth_date: card.birth_date ?? undefined,
    region: card.region ?? undefined,
    card_issue_date: card.card_issue_date ?? undefined,
    join_date: card.join_date ?? undefined,
    exclusion_year: card.exclusion_year,
    chairman: card.chairman ?? undefined,
    photo_shape: card.photo_shape,
    logo_shape: card.logo_shape,
    bg_kind: card.bg_kind,
    bg_color: card.bg_color ?? undefined,
    bg_gradient: card.bg_gradient ?? undefined,
    avatar_color: card.avatar_color,
    avatar_gradient: card.avatar_gradient,
    label_set: card.label_set,
    field_order: card.field_order,
    contacts: card.contacts,
    internal_blocks: card.internal_blocks,
    hide_birth_date: card.hide_birth_date,
    hide_region: card.hide_region,
    hide_card_issue_date: card.hide_card_issue_date,
    hide_join_date: card.hide_join_date,
    hide_chairman: card.hide_chairman,
    feedback_form_enabled: card.feedback_form_enabled,
    logo_key: card.logo_key,
    photo_key: card.photo_key,
  };
}

/** Служебные данные видны только в админке — на публичную карточку они не уходят. */
function InternalInfoPanel({ card, categoryName }: { card: Card; categoryName?: string }) {
  const blocks = (card.internal_blocks ?? []).filter((b) => b.value || b.label);
  const rows: { label: string; value: string }[] = [
    ...(categoryName ? [{ label: "Категория", value: categoryName }] : []),
    ...(card.exclusion_year ? [{ label: "Год исключения из СТД", value: String(card.exclusion_year) }] : []),
    ...(card.death_date ? [{ label: "Дата смерти", value: formatDate(card.death_date) }] : []),
    ...blocks.map((b) => ({
      label: b.label || (b.type ? messengerLabel(b.type) : "Поле"),
      value: b.value,
    })),
  ];

  return (
    <section className="rounded-3xl border border-std-border bg-white px-5 py-4">
      <h2 className="text-base font-semibold text-std-ink">Служебная информация</h2>
      <p className="mb-3 text-xs text-std-muted">
        Видна только администраторам. На публичной карточке не отображается.
      </p>
      {rows.length === 0 ? (
        <p className="text-sm text-std-muted-fg">Не заполнена</p>
      ) : (
        <dl className="divide-y divide-std-border">
          {rows.map((row, i) => (
            <div key={`${row.label}-${i}`} className="flex gap-4 py-2">
              <dt className="w-[200px] shrink-0 text-sm text-std-muted-fg">{row.label}</dt>
              <dd className="text-sm text-std-ink break-all">{row.value}</dd>
            </div>
          ))}
        </dl>
      )}
    </section>
  );
}

function InvalidCardViewWithMessage({ card, t }: { card: Card; t: Record<string, string> }) {
  const { data: messages } = useQuery({
    queryKey: ["cardMessages", card.id],
    queryFn: () => cardMessagesApi.list(card.id).then((r) => r.data),
  });
  const latest = messages?.find((m) => !m.deleted_at) ?? null;
  return (
    <InvalidCardView
      card={card}
      membershipLabel={t.membership_card}
      invalidLabel={t.card_invalid}
      contactLabel={t.contact_btn}
      logoAlt={t.logo_alt}
      messageText={latest?.text}
      messageImageUrl={latest?.image_key ? `/api/media/${latest.image_key}` : null}
    />
  );
}

export function CardPreviewPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const canEdit = useAuthStore((s) => s.user?.role) !== "viewer";
  const t = CARD_T;

  const { data: card, isLoading } = useQuery({
    queryKey: ["card", id],
    queryFn: () => cardsApi.get(id!).then((r) => r.data),
    enabled: !!id,
  });

  const { data: categories } = useQuery({
    queryKey: ["categories"],
    queryFn: () => cardsApi.getCategories().then((r) => r.data),
    staleTime: 5 * 60 * 1000,
  });

  const categoryName = categories?.find((c) => c.id === card?.category_id)?.name_ru;

  if (isLoading || !card) {
    return (
      <div className="flex h-[50vh] items-center justify-center">
        <Loader2 className="h-6 w-6 animate-spin text-std-muted-fg" />
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-6 px-4 py-6">
      <div className="grid grid-cols-[1fr_auto_1fr] items-center gap-4">
        <div>
          <Link
            to="/admin/cards"
            className="inline-flex items-center gap-2 text-[14px] font-medium text-std-ink-strong hover:text-std-primary"
          >
            <ArrowLeft className="h-4 w-4" />
            Назад
          </Link>
        </div>

        <div />

        <div className="flex justify-end">
          {canEdit && (
            <Button
              variant="outline"
              size="sm"
              onClick={() => navigate(`/admin/cards/${card.id}/edit`)}
              className="rounded-full"
            >
              <Edit className="mr-2 h-4 w-4" />
              Редактировать
            </Button>
          )}
        </div>
      </div>

      <div className="flex w-full flex-col items-center gap-6">
        <div className="w-full max-w-[340px]">
          {card.is_active ? (
            <MemberCardPreview payload={cardToPayload(card)} />
          ) : (
            <InvalidCardViewWithMessage card={card} t={t} />
          )}
        </div>

        <div className="w-full max-w-[560px]">
          <InternalInfoPanel card={card} categoryName={categoryName} />
        </div>
      </div>
    </div>
  );
}
