import { useNavigate } from "react-router-dom";
import { Copy } from "lucide-react";
import { toast } from "sonner";
import { CardActionMenu } from "@/components/cards/CardActionMenu";
import type { CardListItem } from "@/lib/api/cards";

interface Props {
  card: CardListItem;
  onDelete: (id: string) => void;
  onPublishMessage?: (id: string) => void;
  onAssignTemplate?: (id: string) => void;
}

function getInitials(last: string, first: string): string {
  return `${(last || "").charAt(0)}${(first || "").charAt(0)}`.toUpperCase();
}

export function MemberCardTile({ card, onDelete, onPublishMessage, onAssignTemplate }: Props) {
  const navigate = useNavigate();

  const fullName = [card.last_name, card.first_name, card.middle_name]
    .filter(Boolean)
    .join(" ");

  const year = new Date(card.created_at).getFullYear();
  const initials = getInitials(card.last_name, card.first_name);

  return (
    <div
      className="bg-white rounded-card border border-std-border overflow-hidden flex flex-col cursor-pointer hover:shadow-md transition-shadow"
      onClick={() => navigate(`/admin/cards/${card.id}`)}
    >
      {/* Card header: №/year, full name */}
      <div className="pt-4 pb-3 px-4 flex flex-col gap-0.5 relative">
        <div className="absolute top-3 right-3">
          <CardActionMenu
            card={card}
            onDelete={onDelete}
            onPublishMessage={onPublishMessage}
            onAssignTemplate={onAssignTemplate}
            triggerClassName="w-8 h-8 rounded-full bg-std-surface-3 border border-std-border hover:bg-std-surface-2 transition-colors flex items-center justify-center"
          />
        </div>

        <p className="text-[11px] font-medium text-std-muted-fg leading-tight">
          №{card.membership_no} с {year} г.
        </p>
        <p className="text-sm font-semibold text-std-ink-strong truncate pr-8 leading-snug">
          {fullName}
        </p>
        {card.public_slug && (() => {
          const fullUrl = `${window.location.origin}/c/${card.public_slug}`;
          const displayUrl = fullUrl.replace(/^https?:\/\//, "");
          const handleCopy = async (e: React.MouseEvent) => {
            e.stopPropagation();
            try {
              await navigator.clipboard.writeText(fullUrl);
              toast.success("Ссылка скопирована");
            } catch {
              toast.error("Не удалось скопировать");
            }
          };
          return (
            <button
              type="button"
              onClick={handleCopy}
              className="inline-flex items-center gap-[2px] text-xs font-normal text-std-primary hover:opacity-80 truncate mt-0.5 max-w-full"
              title={fullUrl}
            >
              <span className="truncate">{displayUrl}</span>
              <Copy className="size-3 shrink-0" />
            </button>
          );
        })()}
      </div>

      {/* Card body: monogram inside light rounded square + bottom name */}
      <div className="flex flex-col items-center justify-center gap-3 pt-2 pb-5 px-4 flex-1 bg-std-surface-2">
        <p className="text-[11px] font-medium text-std-muted-fg">
          Членский билет №{card.membership_no}
        </p>

        <div
          className="w-[88px] h-[88px] flex items-center justify-center shrink-0 bg-white"
          style={{ borderRadius: 14 }}
        >
          {card.photo_key ? (
            <img
              src={`/api/media/${card.photo_key}`}
              alt={fullName}
              className="w-full h-full object-cover"
              style={{ borderRadius: 14 }}
            />
          ) : (
            <span className="text-2xl font-bold text-std-ink-strong tracking-tight">
              {initials}
            </span>
          )}
        </div>

        <p className="text-xs font-semibold text-std-ink-strong text-center truncate max-w-full px-2">
          {fullName}
        </p>
      </div>
    </div>
  );
}
