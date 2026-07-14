import { useEffect, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import { cardsApi } from "@/lib/api/cards";
import { templatesApi } from "@/lib/api/templates";

interface Props {
  open: boolean;
  cardId: string | null;
  onClose: () => void;
}

export function AssignTemplateDialog({ open, cardId, onClose }: Props) {
  const qc = useQueryClient();
  const [selected, setSelected] = useState<string | null>(null);

  useEffect(() => {
    if (!open) setSelected(null);
  }, [open]);

  const { data: templates, isLoading } = useQuery({
    queryKey: ["templates"],
    queryFn: () => templatesApi.list().then((r) => r.data),
    enabled: open,
  });

  const mutation = useMutation({
    mutationFn: ({ id, tplId }: { id: string; tplId: string }) =>
      cardsApi.applyTemplate(id, tplId).then((r) => r.data),
    onSuccess: () => {
      toast.success("Шаблон применён");
      qc.invalidateQueries({ queryKey: ["cards"] });
      onClose();
    },
    onError: (err: unknown) => {
      const message =
        err && typeof err === "object" && "response" in err
          ? (err as { response?: { data?: { message?: string } } }).response?.data?.message
          : undefined;
      toast.error(message || "Не удалось применить шаблон");
    },
  });

  function handleConfirm() {
    if (!cardId || !selected) return;
    mutation.mutate({ id: cardId, tplId: selected });
  }

  return (
    <Dialog open={open} onOpenChange={(o) => !o && !mutation.isPending && onClose()}>
      <DialogContent className="max-w-md">
        <DialogHeader>
          <DialogTitle>Назначить шаблон</DialogTitle>
          <DialogDescription>
            Будут заполнены только пустые поля; уже заполненные значения сохранятся.
          </DialogDescription>
        </DialogHeader>

        <div className="max-h-72 overflow-y-auto space-y-1 pr-1">
          {isLoading && <p className="text-sm text-muted-foreground">Загрузка…</p>}
          {!isLoading && (templates?.length ?? 0) === 0 && (
            <p className="text-sm text-muted-foreground">Шаблонов пока нет</p>
          )}
          {templates?.map((tpl) => {
            const active = selected === tpl.id;
            return (
              <button
                key={tpl.id}
                type="button"
                onClick={() => setSelected(tpl.id)}
                className={cn(
                  "w-full text-left rounded-md border px-3 py-2 transition-colors flex items-center gap-3",
                  active
                    ? "border-std-primary bg-std-surface-2"
                    : "border-std-border hover:bg-std-surface-2",
                )}
              >
                <span className="text-sm font-medium flex-1">{tpl.name}</span>
                {tpl.is_default && (
                  <span className="text-xs text-muted-foreground">по умолчанию</span>
                )}
              </button>
            );
          })}
        </div>

        <DialogFooter>
          <Button type="button" variant="outline" onClick={onClose} disabled={mutation.isPending}>
            Отмена
          </Button>
          <Button
            type="button"
            onClick={handleConfirm}
            disabled={!selected || mutation.isPending}
            className="bg-std-primary hover:bg-std-primary/90 text-white"
          >
            {mutation.isPending ? "Применяем…" : "Назначить"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
