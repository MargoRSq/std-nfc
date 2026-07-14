import { useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useNavigate } from "react-router-dom";
import { toast } from "sonner";
import {
  Copy,
  Download,
  Edit,
  MoreHorizontal,
  Pencil,
  Plus,
  Trash2,
  Upload,
} from "lucide-react";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Dialog, DialogContent, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { templatesApi, type Template, type TemplateDeleteCascade } from "@/lib/api/templates";
import { importsApi } from "@/lib/api/imports";
import { cn } from "@/lib/utils";

interface Props {
  template: Template;
  defaultCategoryId?: number | null;
  triggerClassName?: string;
}

export function TemplateActionMenu({ template, defaultCategoryId, triggerClassName }: Props) {
  const qc = useQueryClient();
  const navigate = useNavigate();
  const [renameOpen, setRenameOpen] = useState(false);
  const [renameValue, setRenameValue] = useState(template.name);
  const [deleteOpen, setDeleteOpen] = useState(false);
  const [deleteCascade, setDeleteCascade] = useState<TemplateDeleteCascade>("template_only");

  const duplicateMutation = useMutation({
    mutationFn: () =>
      templatesApi.create({
        name: `${template.name} (копия)`,
        category_id: template.category_id ?? defaultCategoryId ?? 1,
        default_fields: template.default_fields,
        default_styles: template.default_styles,
      }),
    onSuccess: () => {
      toast.success("Шаблон дублирован");
      void qc.invalidateQueries({ queryKey: ["templates"] });
    },
    onError: () => toast.error("Ошибка при дублировании"),
  });

  const renameMutation = useMutation({
    mutationFn: (name: string) => templatesApi.update(template.id, { name }),
    onSuccess: () => {
      toast.success("Шаблон переименован");
      void qc.invalidateQueries({ queryKey: ["templates"] });
      setRenameOpen(false);
    },
    onError: () => toast.error("Ошибка при переименовании"),
  });

  const deleteMutation = useMutation({
    mutationFn: (cascade: TemplateDeleteCascade) =>
      templatesApi.delete(template.id, cascade).then((r) => r.data),
    onSuccess: (data) => {
      if (data.cards_deleted > 0) {
        toast.success(`Шаблон и ${data.cards_deleted} карточек удалены`);
      } else if (data.cards_reassigned > 0) {
        toast.success(`Шаблон удалён, ${data.cards_reassigned} карточек переведены на дефолтный`);
      } else {
        toast.success("Шаблон удалён");
      }
      void qc.invalidateQueries({ queryKey: ["templates"] });
      void qc.invalidateQueries({ queryKey: ["cards"] });
      setDeleteOpen(false);
    },
    onError: (err: unknown) => {
      const e = err as { response?: { data?: { detail?: string } } };
      toast.error(e?.response?.data?.detail ?? "Ошибка при удалении");
    },
  });

  function handleDownloadTemplate() {
    importsApi
      .downloadTemplate()
      .then((r) => {
        const url = URL.createObjectURL(r.data as Blob);
        const a = document.createElement("a");
        a.href = url;
        a.download = "template.xlsx";
        a.click();
        URL.revokeObjectURL(url);
      })
      .catch(() => toast.error("Не удалось скачать шаблон"));
  }

  function stop(e: React.MouseEvent | React.PointerEvent) {
    e.stopPropagation();
  }

  return (
    <>
      <DropdownMenu>
        <DropdownMenuTrigger asChild>
          <button
            type="button"
            onClick={stop}
            className={cn(
              "w-9 h-9 rounded-full flex items-center justify-center hover:bg-std-surface-2 shrink-0",
              triggerClassName,
            )}
            aria-label="Действия"
          >
            <MoreHorizontal className="w-4 h-4 text-std-muted-fg" />
          </button>
        </DropdownMenuTrigger>
        <DropdownMenuContent align="end" onClick={stop}>
          <DropdownMenuItem
            onClick={() => {
              setRenameValue(template.name);
              setRenameOpen(true);
            }}
          >
            <Pencil className="mr-2 h-4 w-4" />
            Переименовать
          </DropdownMenuItem>
          <DropdownMenuItem onClick={() => navigate(`/admin/cards/new?template_id=${template.id}`)}>
            <Plus className="mr-2 h-4 w-4" />
            Создать удостоверение
          </DropdownMenuItem>
          <DropdownMenuItem onClick={() => navigate(`/admin/import?template_id=${template.id}`)}>
            <Upload className="mr-2 h-4 w-4" />
            Загрузить данные Excel
          </DropdownMenuItem>
          <DropdownMenuItem onClick={handleDownloadTemplate}>
            <Download className="mr-2 h-4 w-4" />
            Скачать шаблон таблицы Excel
          </DropdownMenuItem>
          <DropdownMenuItem onClick={() => navigate(`/admin/templates/${template.id}/edit`)}>
            <Edit className="mr-2 h-4 w-4" />
            Редактировать
          </DropdownMenuItem>
          <DropdownMenuItem onClick={() => duplicateMutation.mutate()}>
            <Copy className="mr-2 h-4 w-4" />
            Дублировать
          </DropdownMenuItem>
          {!template.is_default && (
            <>
              <DropdownMenuSeparator />
              <DropdownMenuItem
                className="text-destructive focus:text-destructive"
                onClick={() => {
                  setDeleteCascade("template_only");
                  setDeleteOpen(true);
                }}
              >
                <Trash2 className="mr-2 h-4 w-4" />
                Удалить шаблон
              </DropdownMenuItem>
            </>
          )}
        </DropdownMenuContent>
      </DropdownMenu>

      <Dialog open={renameOpen} onOpenChange={setRenameOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Переименовать шаблон</DialogTitle>
          </DialogHeader>
          <p className="text-sm text-muted-foreground -mt-2">
            Здесь вы можете изменить название шаблона
          </p>
          <Input
            autoFocus
            value={renameValue}
            onChange={(e) => setRenameValue(e.target.value)}
            placeholder="Введите новое название шаблона"
          />
          <DialogFooter>
            <Button variant="outline" onClick={() => setRenameValue(template.name)}>
              Сбросить изменения
            </Button>
            <Button
              disabled={
                renameMutation.isPending ||
                !renameValue.trim() ||
                renameValue.trim() === template.name
              }
              onClick={() => renameMutation.mutate(renameValue.trim())}
            >
              Сохранить
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <Dialog open={deleteOpen} onOpenChange={setDeleteOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Удалить шаблон?</DialogTitle>
          </DialogHeader>
          <p className="text-sm text-muted-foreground">
            Вы уверены, что хотите удалить этот шаблон?
          </p>
          <div className="flex flex-col gap-2 mt-2">
            <label
              className={`flex items-start gap-3 p-3 rounded-xl border cursor-pointer transition-colors ${
                deleteCascade === "template_only"
                  ? "border-std-primary bg-std-surface-selected"
                  : "border-std-border hover:border-std-primary"
              }`}
            >
              <input
                type="radio"
                name="deleteCascade"
                checked={deleteCascade === "template_only"}
                onChange={() => setDeleteCascade("template_only")}
                className="mt-1 accent-std-primary"
              />
              <div className="text-sm">
                <p className="font-medium text-foreground">Удалить только шаблон</p>
                <p className="text-xs text-muted-foreground mt-0.5">
                  Карточки будут адаптированы под шаблон по умолчанию
                </p>
              </div>
            </label>
            <label
              className={`flex items-start gap-3 p-3 rounded-xl border cursor-pointer transition-colors ${
                deleteCascade === "with_cards"
                  ? "border-std-primary bg-std-surface-selected"
                  : "border-std-border hover:border-std-primary"
              }`}
            >
              <input
                type="radio"
                name="deleteCascade"
                checked={deleteCascade === "with_cards"}
                onChange={() => setDeleteCascade("with_cards")}
                className="mt-1 accent-std-primary"
              />
              <div className="text-sm">
                <p className="font-medium text-foreground">Удалить шаблон и карточки</p>
                <p className="text-xs text-muted-foreground mt-0.5">
                  Все карточки, созданные по нему, будут удалены
                </p>
              </div>
            </label>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setDeleteOpen(false)}>
              Оставить
            </Button>
            <Button
              variant="destructive"
              disabled={deleteMutation.isPending}
              onClick={() => deleteMutation.mutate(deleteCascade)}
            >
              Удалить
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  );
}
