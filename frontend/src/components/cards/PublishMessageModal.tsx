import { useEffect, useRef, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { ImagePlus, Trash2, X } from "lucide-react";
import { toast } from "sonner";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import { Label } from "@/components/ui/label";
import { cardMessagesApi } from "@/lib/api/cardMessages";
import { cardsApi } from "@/lib/api/cards";
import { InvalidCardView } from "./InvalidCardView";

interface Props {
  cardId: string | null;
  open: boolean;
  onOpenChange: (next: boolean) => void;
}

const MAX_BYTES = 5 * 1024 * 1024;

export function PublishMessageModal({ cardId, open, onOpenChange }: Props) {
  const qc = useQueryClient();
  const fileInputRef = useRef<HTMLInputElement | null>(null);
  const [text, setText] = useState("");
  const [file, setFile] = useState<File | null>(null);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [existingImageUrl, setExistingImageUrl] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [deactivate, setDeactivate] = useState(true);

  const { data: card } = useQuery({
    queryKey: ["card", cardId],
    queryFn: () => cardsApi.get(cardId!).then((r) => r.data),
    enabled: !!cardId && open,
  });

  const { data: messages } = useQuery({
    queryKey: ["cardMessages", cardId],
    queryFn: () => cardMessagesApi.list(cardId!).then((r) => r.data),
    enabled: !!cardId && open,
  });

  const activeMessage = messages?.[0] ?? null;
  const hasPublished = !!activeMessage;

  useEffect(() => {
    if (!open) return;
    if (activeMessage) {
      setText(activeMessage.text ?? "");
      setExistingImageUrl(
        activeMessage.image_key ? `/api/media/${activeMessage.image_key}` : null,
      );
      setDeactivate(card ? !card.is_active : true);
    } else {
      setText("");
      setExistingImageUrl(null);
      setDeactivate(true);
    }
  }, [activeMessage?.id, open, card?.is_active]);

  function reset() {
    setText("");
    setFile(null);
    if (previewUrl) URL.revokeObjectURL(previewUrl);
    setPreviewUrl(null);
    setExistingImageUrl(null);
    setError(null);
    setDeactivate(true);
  }

  const publishMutation = useMutation({
    mutationFn: () => {
      if (!cardId) throw new Error("no cardId");
      return cardMessagesApi.publish(cardId, text.trim(), file, deactivate);
    },
    onSuccess: () => {
      toast.success(deactivate ? "Сообщение опубликовано, удостоверение недействительно" : "Сообщение опубликовано");
      void qc.invalidateQueries({ queryKey: ["cardMessages", cardId] });
      void qc.invalidateQueries({ queryKey: ["cards"] });
      void qc.invalidateQueries({ queryKey: ["card", cardId] });
      reset();
      onOpenChange(false);
    },
    onError: () => {
      toast.error("Не удалось опубликовать сообщение");
    },
  });

  const deleteMutation = useMutation({
    mutationFn: () => {
      if (!cardId || !activeMessage) throw new Error("no message");
      return cardMessagesApi.remove(cardId, activeMessage.id);
    },
    onSuccess: () => {
      toast.success("Сообщение удалено, удостоверение восстановлено");
      void qc.invalidateQueries({ queryKey: ["cardMessages", cardId] });
      void qc.invalidateQueries({ queryKey: ["cards"] });
      void qc.invalidateQueries({ queryKey: ["card", cardId] });
      reset();
      onOpenChange(false);
    },
    onError: () => {
      toast.error("Не удалось удалить сообщение");
    },
  });

  function handleFileChange(e: React.ChangeEvent<HTMLInputElement>) {
    const f = e.target.files?.[0] ?? null;
    if (!f) return;
    if (f.size > MAX_BYTES) {
      setError("Изображение больше 5 МБ");
      return;
    }
    if (!/^image\/(jpeg|png|webp)$/.test(f.type)) {
      setError("Поддерживаются только JPEG, PNG, WEBP");
      return;
    }
    setError(null);
    setFile(f);
    if (previewUrl) URL.revokeObjectURL(previewUrl);
    setPreviewUrl(URL.createObjectURL(f));
  }

  function handleSubmit() {
    const trimmed = text.trim();
    if (!trimmed && !file) {
      setError("Введите текст или прикрепите изображение");
      return;
    }
    setError(null);
    publishMutation.mutate();
  }

  function handleOpenChange(next: boolean) {
    if (!next) reset();
    onOpenChange(next);
  }

  function clearFile() {
    setFile(null);
    if (previewUrl) URL.revokeObjectURL(previewUrl);
    setPreviewUrl(null);
    setExistingImageUrl(null);
    if (fileInputRef.current) fileInputRef.current.value = "";
  }

  const displayImageUrl = previewUrl ?? existingImageUrl;

  return (
    <Dialog open={open} onOpenChange={handleOpenChange}>
      <DialogContent className="max-w-3xl">
        <DialogHeader>
          <DialogTitle>
            {hasPublished ? "Редактировать сообщение" : "Опубликовать сообщение?"}
          </DialogTitle>
          <DialogDescription>
            {hasPublished
              ? "Измените сообщение или удалите его, чтобы восстановить удостоверение"
              : "Введите текст, который будет отображаться в карточке"}
          </DialogDescription>
        </DialogHeader>
        <div className="grid grid-cols-1 gap-6 md:grid-cols-[1fr_280px]">
          <div className="space-y-3">
            <textarea
              value={text}
              onChange={(e) => setText(e.target.value)}
              placeholder="Введите текст сообщения"
              maxLength={2000}
              rows={4}
              className="w-full rounded-2xl border border-std-border px-4 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-std-primary resize-none"
            />

            {displayImageUrl ? (
              <div className="relative rounded-2xl overflow-hidden border border-std-border">
                <img
                  src={displayImageUrl}
                  alt="Превью"
                  className="w-full max-h-60 object-cover"
                />
                <button
                  type="button"
                  onClick={clearFile}
                  className="absolute top-2 right-2 w-7 h-7 rounded-full bg-black/60 text-white flex items-center justify-center hover:bg-black/75"
                  aria-label="Удалить изображение"
                >
                  <X className="w-4 h-4" />
                </button>
              </div>
            ) : (
              <button
                type="button"
                onClick={() => fileInputRef.current?.click()}
                className="w-full rounded-2xl border border-dashed border-std-border px-4 py-3 text-sm text-std-primary flex items-center justify-center gap-2 hover:bg-std-surface-2"
              >
                <ImagePlus className="w-4 h-4" />
                Загрузить картинку
              </button>
            )}
            <input
              ref={fileInputRef}
              type="file"
              accept="image/jpeg,image/png,image/webp"
              className="hidden"
              onChange={handleFileChange}
            />

            {error && <p className="text-sm text-destructive">{error}</p>}

            <div className="flex items-center gap-2 pt-1">
              <Checkbox
                id="deactivate-card"
                checked={deactivate}
                onCheckedChange={(v) => setDeactivate(!!v)}
              />
              <Label htmlFor="deactivate-card" className="text-sm cursor-pointer">
                Сделать удостоверение недействительным
              </Label>
            </div>

            <Button
              onClick={handleSubmit}
              disabled={publishMutation.isPending || deleteMutation.isPending}
              className="w-full"
            >
              {publishMutation.isPending
                ? "Публикуем…"
                : hasPublished
                  ? "Обновить сообщение"
                  : "Опубликовать"}
            </Button>

            {hasPublished && (
              <Button
                variant="outline"
                onClick={() => deleteMutation.mutate()}
                disabled={deleteMutation.isPending || publishMutation.isPending}
                className="w-full border-destructive text-destructive hover:bg-destructive/10 hover:text-destructive"
              >
                <Trash2 className="mr-2 h-4 w-4" />
                {deleteMutation.isPending ? "Удаляем…" : "Удалить сообщение"}
              </Button>
            )}
          </div>

          <div className="space-y-2">
            <p className="text-xs font-medium text-std-muted-fg">Превью карты-заглушки</p>
            {card ? (
              <InvalidCardView
                card={card}
                membershipLabel="Членский билет"
                invalidLabel="Удостоверение недействительно"
                contactLabel="Связаться с СТД"
                logoAlt="СТД"
                messageText={text}
                messageImageUrl={displayImageUrl}
              />
            ) : (
              <div className="rounded-2xl border border-dashed border-std-border h-80 flex items-center justify-center text-xs text-std-muted-fg">
                Загрузка…
              </div>
            )}
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
}
