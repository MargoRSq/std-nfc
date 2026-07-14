import { useEffect, useMemo, useState } from "react";
import { Check, ChevronRight, Loader2, Trash2, X } from "lucide-react";
import {
  Dialog,
  DialogContent,
  DialogTitle,
  DialogDescription,
} from "@/components/ui/dialog";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { cn } from "@/lib/utils";
import {
  LABEL_PRESET_TYPE_OPTIONS,
  SYSTEM_LABEL_PRESETS,
  useCreateLabelPreset,
  useDeleteLabelPreset,
  useLabelPresets,
  type LabelPresetType,
} from "@/lib/api/labelPresets";

interface Props {
  open: boolean;
  onClose: () => void;
  onApply: (name: string, type: LabelPresetType) => void;
}

export function LabelPickerSheet({ open, onClose, onApply }: Props) {
  const [draft, setDraft] = useState("");
  const [draftType, setDraftType] = useState<LabelPresetType>("text");
  const { data: userPresets, isLoading } = useLabelPresets();
  const create = useCreateLabelPreset();
  const del = useDeleteLabelPreset();

  useEffect(() => {
    if (!open) {
      setDraft("");
      setDraftType("text");
    }
  }, [open]);

  const trimmed = draft.trim();
  const canSubmit = trimmed.length > 0 && !create.isPending;

  const { userList, systemList } = useMemo(() => {
    const sortedUser = (userPresets ?? [])
      .slice()
      .sort((a, b) => (b.created_at || "").localeCompare(a.created_at || ""));
    const userNames = new Set(sortedUser.map((p) => p.name.toLowerCase()));
    const systemFiltered = SYSTEM_LABEL_PRESETS.filter(
      (s) => !userNames.has(s.name.toLowerCase()),
    );
    return { userList: sortedUser, systemList: systemFiltered };
  }, [userPresets]);

  const hasAny = userList.length > 0 || systemList.length > 0;

  async function handleCreate() {
    if (!canSubmit) return;
    const preset = await create.mutateAsync({ name: trimmed, type: draftType });
    onApply(preset.name, preset.type);
    onClose();
  }

  function handlePick(name: string, type: LabelPresetType) {
    onApply(name, type);
    onClose();
  }

  return (
    <Dialog open={open} onOpenChange={(v) => !v && onClose()}>
      <DialogContent className="max-w-md gap-0 rounded-3xl border border-std-border bg-white p-0 shadow-xl sm:rounded-3xl [&>button[aria-label='Close']]:hidden [&>button.absolute]:hidden">
        <div className="flex items-center justify-between px-5 pb-2 pt-5">
          <DialogTitle className="text-lg font-semibold text-std-ink">
            Новая этикетка
          </DialogTitle>
          <DialogDescription className="sr-only">
            Создайте новую этикетку или выберите из сохранённых
          </DialogDescription>
          <button
            type="button"
            onClick={onClose}
            aria-label="Закрыть"
            className="flex h-10 w-10 items-center justify-center rounded-full border border-std-border bg-white text-std-primary hover:bg-std-surface-2"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        <div className="space-y-3 px-5 py-4">
          <div className="flex items-center gap-3">
            <div className="relative flex-1 rounded-xl border border-std-border bg-white px-4 py-3">
              <input
                value={draft}
                onChange={(e) => setDraft(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === "Enter") {
                    e.preventDefault();
                    void handleCreate();
                  }
                }}
                placeholder="Введите название новой этикетки"
                className="h-7 w-full border-0 bg-transparent px-0 pr-7 text-base placeholder:text-std-muted-fg focus:outline-none"
                autoFocus
              />
              {draft && (
                <button
                  type="button"
                  aria-label="Очистить"
                  onClick={() => setDraft("")}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground"
                >
                  <X className="h-4 w-4" />
                </button>
              )}
            </div>
            <button
              type="button"
              onClick={() => void handleCreate()}
              disabled={!canSubmit}
              aria-label="Сохранить этикетку"
              className={cn(
                "flex h-12 w-12 shrink-0 items-center justify-center rounded-full border-2 transition-colors",
                canSubmit
                  ? "border-std-primary bg-std-primary text-white hover:bg-std-primary/90"
                  : "border-std-border bg-white text-std-muted-fg",
              )}
            >
              {create.isPending ? (
                <Loader2 className="h-5 w-5 animate-spin" />
              ) : (
                <Check className="h-5 w-5" strokeWidth={2.5} />
              )}
            </button>
          </div>

          <div className="flex items-center gap-3">
            <label className="text-sm font-medium text-std-muted-fg w-20 shrink-0">Тип</label>
            <Select value={draftType} onValueChange={(v) => setDraftType(v as LabelPresetType)}>
              <SelectTrigger className="rounded-xl border-std-border bg-white">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {LABEL_PRESET_TYPE_OPTIONS.map((opt) => (
                  <SelectItem key={opt.value} value={opt.value}>
                    {opt.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          <button
            type="button"
            onClick={() => void handleCreate()}
            disabled={!canSubmit}
            className={cn(
              "h-11 w-full rounded-xl border border-std-border bg-white text-sm font-semibold transition-colors",
              canSubmit
                ? "text-std-primary hover:bg-std-surface-2"
                : "text-std-muted-fg",
            )}
          >
            Сохранить
          </button>
        </div>

        <div className="h-px bg-std-border" />

        <div className="max-h-72 overflow-y-auto px-5 py-3 space-y-3">
          {isLoading && (
            <div className="flex justify-center py-6 text-std-muted-fg">
              <Loader2 className="h-5 w-5 animate-spin" />
            </div>
          )}
          {!isLoading && !hasAny && (
            <div className="py-6 text-center text-sm text-std-muted-fg">
              Нет сохранённых этикеток
            </div>
          )}

          {userList.length > 0 && (
            <div className="space-y-2">
              <div className="px-1 text-xs font-semibold uppercase tracking-wide text-std-muted-fg">
                Мои этикетки
              </div>
              {userList.map((p) => {
                const typeLabel = LABEL_PRESET_TYPE_OPTIONS.find((o) => o.value === p.type)?.label;
                return (
                  <button
                    key={p.id}
                    type="button"
                    onClick={() => handlePick(p.name, p.type)}
                    aria-label={`Применить «${p.name}»`}
                    className="flex w-full items-center gap-2 rounded-xl border border-std-border bg-white px-4 py-3 text-left transition-colors hover:bg-std-surface-2"
                  >
                    <div className="flex-1 min-w-0">
                      <div className="truncate text-base text-std-ink">{p.name}</div>
                      {typeLabel && (
                        <div className="text-xs text-std-muted-fg">{typeLabel}</div>
                      )}
                    </div>
                    <span
                      role="button"
                      tabIndex={0}
                      aria-label={`Удалить «${p.name}»`}
                      onClick={(e) => {
                        e.stopPropagation();
                        if (!del.isPending) void del.mutate(p.id);
                      }}
                      onKeyDown={(e) => {
                        if (e.key === "Enter" || e.key === " ") {
                          e.preventDefault();
                          e.stopPropagation();
                          if (!del.isPending) void del.mutate(p.id);
                        }
                      }}
                      className={cn(
                        "text-[#DC2626] hover:text-[#DC2626]/80",
                        del.isPending && "opacity-50 pointer-events-none",
                      )}
                    >
                      <Trash2 className="h-5 w-5" />
                    </span>
                    <ChevronRight className="h-5 w-5 text-std-primary" />
                  </button>
                );
              })}
            </div>
          )}

          {userList.length > 0 && systemList.length > 0 && (
            <div className="h-px bg-std-border" />
          )}

          {systemList.length > 0 && (
            <div className="space-y-2">
              <div className="px-1 text-xs font-semibold uppercase tracking-wide text-std-muted-fg">
                Стандартные
              </div>
              {systemList.map((p) => {
                const typeLabel = LABEL_PRESET_TYPE_OPTIONS.find((o) => o.value === p.type)?.label;
                return (
                  <button
                    key={p.id}
                    type="button"
                    onClick={() => handlePick(p.name, p.type)}
                    aria-label={`Применить «${p.name}»`}
                    className="flex w-full items-center gap-2 rounded-xl border border-std-border bg-white px-4 py-3 text-left transition-colors hover:bg-std-surface-2"
                  >
                    <div className="flex-1 min-w-0">
                      <div className="truncate text-base text-std-ink">{p.name}</div>
                      {typeLabel && (
                        <div className="text-xs text-std-muted-fg">{typeLabel}</div>
                      )}
                    </div>
                    <ChevronRight className="h-5 w-5 text-std-primary" />
                  </button>
                );
              })}
            </div>
          )}
        </div>
      </DialogContent>
    </Dialog>
  );
}
