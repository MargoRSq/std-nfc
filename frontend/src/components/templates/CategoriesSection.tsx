import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { Eye, EyeOff, Pencil } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { categoriesApi, type Category } from "@/lib/api/categories";
import { useAuthStore } from "@/stores/authStore";

function usageLabel(cat: Category) {
  const parts: string[] = [];
  if (cat.cards_count > 0) parts.push(`карточек: ${cat.cards_count}`);
  if (cat.templates_count > 0) parts.push(`шаблонов: ${cat.templates_count}`);
  return parts.length ? parts.join(", ") : "не используется";
}

export function CategoriesSection() {
  const qc = useQueryClient();
  const isSuperAdmin = useAuthStore((s) => s.user?.role) === "super_admin";
  const [editingId, setEditingId] = useState<number | null>(null);
  const [draft, setDraft] = useState("");

  const { data: categories } = useQuery({
    queryKey: ["categories"],
    queryFn: () => categoriesApi.list().then((r) => r.data),
  });

  const mutation = useMutation({
    mutationFn: ({ id, ...data }: { id: number; name_ru?: string; is_hidden?: boolean }) =>
      categoriesApi.update(id, data).then((r) => r.data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["categories"] });
      qc.invalidateQueries({ queryKey: ["cards"] });
      setEditingId(null);
    },
    onError: () => toast.error("Не удалось сохранить категорию"),
  });

  if (!categories?.length) return null;

  function startEdit(cat: Category) {
    setEditingId(cat.id);
    setDraft(cat.name_ru);
  }

  function saveEdit(cat: Category) {
    const name = draft.trim();
    if (!name || name === cat.name_ru) {
      setEditingId(null);
      return;
    }
    mutation.mutate({ id: cat.id, name_ru: name });
  }

  return (
    <section className="rounded-3xl border border-std-border bg-white px-4 py-3">
      <h2 className="text-base font-semibold text-std-ink">Категории</h2>
      <p className="text-xs text-std-muted mb-3">
        Категории — уровни членства для фильтра и прав доступа. Скрытые не показываются
        в фильтре списка карточек.
      </p>
      <div className="divide-y divide-std-border">
        {categories.map((cat) => (
          <div key={cat.id} className="flex items-center gap-3 py-2">
            {cat.color_hex && (
              <span
                className="h-3 w-3 rounded-full shrink-0"
                style={{ background: cat.color_hex }}
                aria-hidden
              />
            )}
            {editingId === cat.id ? (
              <Input
                autoFocus
                value={draft}
                onChange={(e) => setDraft(e.target.value)}
                onBlur={() => saveEdit(cat)}
                onKeyDown={(e) => {
                  if (e.key === "Enter") saveEdit(cat);
                  if (e.key === "Escape") setEditingId(null);
                }}
                className="h-8 max-w-[240px]"
              />
            ) : (
              <span className={cat.is_hidden ? "text-std-muted line-through" : ""}>
                {cat.name_ru}
              </span>
            )}
            <span className="text-xs text-std-muted">{usageLabel(cat)}</span>
            <div className="flex-1" />
            {isSuperAdmin && (
              <>
                <Button
                  type="button"
                  variant="ghost"
                  size="sm"
                  onClick={() => startEdit(cat)}
                  aria-label={`Переименовать «${cat.name_ru}»`}
                >
                  <Pencil className="size-4" />
                </Button>
                <Button
                  type="button"
                  variant="ghost"
                  size="sm"
                  disabled={mutation.isPending}
                  onClick={() => mutation.mutate({ id: cat.id, is_hidden: !cat.is_hidden })}
                  aria-label={cat.is_hidden ? "Показать категорию" : "Скрыть категорию"}
                >
                  {cat.is_hidden ? <EyeOff className="size-4" /> : <Eye className="size-4" />}
                </Button>
              </>
            )}
          </div>
        ))}
      </div>
    </section>
  );
}
