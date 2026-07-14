import { useNavigate } from "react-router-dom";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { BarChart3, Eye, LayoutTemplate, Edit, MessageSquareOff, MessageSquarePlus, Trash2, MoreHorizontal } from "lucide-react";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Button } from "@/components/ui/button";
import type { CardListItem } from "@/lib/api/cards";
import { cardMessagesApi } from "@/lib/api/cardMessages";

interface Props {
  card: Pick<CardListItem, "id" | "public_slug"> & { is_active?: boolean };
  onDelete: (id: string) => void;
  onAssignTemplate?: (id: string) => void;
  onPublishMessage?: (id: string) => void;
  triggerClassName?: string;
  align?: "start" | "center" | "end";
}

export function CardActionMenu({
  card,
  onDelete,
  onAssignTemplate,
  onPublishMessage,
  triggerClassName,
  align = "end",
}: Props) {
  const navigate = useNavigate();
  const qc = useQueryClient();
  const hasPublishedMessage = card.is_active === false;

  const unpublishMutation = useMutation({
    mutationFn: async () => {
      const list = await cardMessagesApi.list(card.id).then((r) => r.data);
      const active = list?.[0];
      if (!active) throw new Error("no active message");
      return cardMessagesApi.remove(card.id, active.id);
    },
    onSuccess: () => {
      toast.success("Сообщение удалено, удостоверение восстановлено");
      void qc.invalidateQueries({ queryKey: ["cards"] });
      void qc.invalidateQueries({ queryKey: ["card", card.id] });
      void qc.invalidateQueries({ queryKey: ["cardMessages", card.id] });
    },
    onError: () => toast.error("Не удалось удалить сообщение"),
  });

  function handleView() {
    window.open(`/c/${card.public_slug}`, "_blank", "noopener,noreferrer");
  }

  function handleAssignTemplate() {
    if (onAssignTemplate) {
      onAssignTemplate(card.id);
      return;
    }
    toast.info("Назначение шаблона скоро будет доступно");
  }

  function handleEdit() {
    navigate(`/admin/cards/${card.id}/edit`);
  }

  function handlePublishMessage() {
    if (onPublishMessage) {
      onPublishMessage(card.id);
      return;
    }
    toast.info("Публикация сообщений скоро будет доступна");
  }

  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button
          variant="ghost"
          size="icon"
          aria-label="Действия с карточкой"
          className={triggerClassName ?? "h-8 w-8"}
          onClick={(e) => e.stopPropagation()}
        >
          <MoreHorizontal className="h-4 w-4" />
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align={align} onClick={(e) => e.stopPropagation()}>
        <DropdownMenuItem onClick={handleView}>
          <Eye className="mr-2 h-4 w-4" />
          Посмотреть карточку
        </DropdownMenuItem>
        <DropdownMenuItem onClick={handleAssignTemplate}>
          <LayoutTemplate className="mr-2 h-4 w-4" />
          Назначить шаблон
        </DropdownMenuItem>
        <DropdownMenuItem onClick={handleEdit}>
          <Edit className="mr-2 h-4 w-4" />
          Редактировать
        </DropdownMenuItem>
        <DropdownMenuItem onClick={handlePublishMessage}>
          <MessageSquarePlus className="mr-2 h-4 w-4" />
          {hasPublishedMessage ? "Редактировать сообщение" : "Опубликовать сообщение"}
        </DropdownMenuItem>
        {hasPublishedMessage && (
          <DropdownMenuItem
            onClick={() => unpublishMutation.mutate()}
            disabled={unpublishMutation.isPending}
          >
            <MessageSquareOff className="mr-2 h-4 w-4" />
            Удалить сообщение
          </DropdownMenuItem>
        )}
        <DropdownMenuItem onClick={() => navigate(`/admin/cards/${card.id}/analytics`)}>
          <BarChart3 className="mr-2 h-4 w-4" />
          Аналитика
        </DropdownMenuItem>
        <DropdownMenuSeparator />
        <DropdownMenuItem
          className="text-destructive focus:text-destructive"
          onClick={() => onDelete(card.id)}
        >
          <Trash2 className="mr-2 h-4 w-4" />
          Удалить
        </DropdownMenuItem>
      </DropdownMenuContent>
    </DropdownMenu>
  );
}
