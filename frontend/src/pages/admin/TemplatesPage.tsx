import { useEffect, useState, useMemo } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import {
  Plus,
  LayoutTemplate,
  Trash2,
  Copy,
  MoreHorizontal,
  ArrowLeft,
  Search,
  Pencil,
  Edit,
  Download,
  Upload,
} from "lucide-react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuSeparator, DropdownMenuTrigger } from "@/components/ui/dropdown-menu";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Form, FormControl, FormField, FormItem, FormLabel, FormMessage } from "@/components/ui/form";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from "@/components/ui/dialog";
import { Skeleton } from "@/components/ui/skeleton";
import { templatesApi, type TemplateDeleteCascade } from "@/lib/api/templates";
import { cardsApi } from "@/lib/api/cards";
import { importsApi } from "@/lib/api/imports";
import { useDebounce } from "@/hooks/useDebounce";

const TEMPLATES_PAGE_SIZE = 12;

// Heuristic tier sort by name prefix; ideally backend would expose a tier_rank field.
const TIER_ORDER = ["платин", "золот", "серебр", "бронз", "умолчан"];
function tierRank(name: string): number {
  const lower = name.toLowerCase();
  for (let i = 0; i < TIER_ORDER.length; i++) {
    if (lower.includes(TIER_ORDER[i])) return i;
  }
  return TIER_ORDER.length;
}

const createSchema = z.object({
  name: z.string().min(1, "Название обязательно"),
});

type CreateFormData = z.infer<typeof createSchema>;

export function TemplatesPage() {
  const qc = useQueryClient();
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();
  const [createOpen, setCreateOpen] = useState(() => searchParams.get("create") === "1");

  useEffect(() => {
    if (searchParams.get("create") === "1") {
      setCreateOpen(true);
      searchParams.delete("create");
      setSearchParams(searchParams, { replace: true });
    }
  }, [searchParams, setSearchParams]);
  const [deleteTarget, setDeleteTarget] = useState<string | null>(null);
  const [deleteCascade, setDeleteCascade] = useState<TemplateDeleteCascade>("template_only");
  const [renameTarget, setRenameTarget] = useState<{ id: string; current: string } | null>(null);
  const [renameValue, setRenameValue] = useState("");
  const [searchRaw, setSearchRaw] = useState("");
  const searchQuery = useDebounce(searchRaw, 300);
  const [currentPage, setCurrentPage] = useState(1);

  const { data: templates, isLoading } = useQuery({
    queryKey: ["templates"],
    queryFn: () => templatesApi.list().then((r) => r.data),
  });

  const { data: categories } = useQuery({
    queryKey: ["categories"],
    queryFn: () => cardsApi.getCategories().then((r) => r.data),
  });

  const createMutation = useMutation({
    mutationFn: (data: CreateFormData) => {
      const categoryId = categories?.[0]?.id;
      if (!categoryId) {
        toast.error("Категории не загружены");
        return Promise.reject(new Error("no categories"));
      }
      return templatesApi.create({ ...data, category_id: categoryId }).then((r) => r.data);
    },
    onSuccess: (template) => {
      toast.success("Шаблон создан");
      void qc.invalidateQueries({ queryKey: ["templates"] });
      setCreateOpen(false);
      navigate(`/admin/templates/${template.id}/edit`);
    },
    onError: () => toast.error("Ошибка при создании шаблона"),
  });

  const renameMutation = useMutation({
    mutationFn: ({ id, name }: { id: string; name: string }) => templatesApi.update(id, { name }),
    onSuccess: () => {
      toast.success("Шаблон переименован");
      void qc.invalidateQueries({ queryKey: ["templates"] });
      setRenameTarget(null);
      setRenameValue("");
    },
    onError: () => toast.error("Ошибка при переименовании"),
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

  const duplicateMutation = useMutation({
    mutationFn: async (id: string) => {
      const tpl = templates?.find((t) => t.id === id);
      if (!tpl) throw new Error("not found");
      return templatesApi.create({
        name: `${tpl.name} (копия)`,
        category_id: tpl.category_id ?? categories?.[0]?.id ?? 1,
        default_fields: tpl.default_fields,
        default_styles: tpl.default_styles,
      });
    },
    onSuccess: () => {
      toast.success("Шаблон дублирован");
      void qc.invalidateQueries({ queryKey: ["templates"] });
    },
    onError: () => toast.error("Ошибка при дублировании"),
  });

  const deleteMutation = useMutation({
    mutationFn: ({ id, cascade }: { id: string; cascade: TemplateDeleteCascade }) =>
      templatesApi.delete(id, cascade).then((r) => r.data),
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
    },
    onError: (err: unknown) => {
      const e = err as { response?: { data?: { detail?: string } } };
      toast.error(e?.response?.data?.detail ?? "Ошибка при удалении");
    },
  });

  const form = useForm<CreateFormData>({
    resolver: zodResolver(createSchema),
    defaultValues: { name: "" },
  });

  const filteredTemplates = useMemo(() => {
    if (!templates) return [];
    const filtered = searchQuery.trim()
      ? templates.filter((t) => t.name.toLowerCase().includes(searchQuery.toLowerCase()))
      : templates;
    return filtered.slice().sort((a, b) => tierRank(a.name) - tierRank(b.name));
  }, [templates, searchQuery]);

  const totalPages = Math.max(1, Math.ceil(filteredTemplates.length / TEMPLATES_PAGE_SIZE));
  const safePage = Math.min(currentPage, totalPages);
  const pagedTemplates = filteredTemplates.slice(
    (safePage - 1) * TEMPLATES_PAGE_SIZE,
    safePage * TEMPLATES_PAGE_SIZE,
  );

  function handleSearchChange(val: string) {
    setSearchRaw(val);
    setCurrentPage(1);
  }

  return (
    <div className="space-y-4 max-w-[1200px] mx-auto">
      {/* Header row: back arrow + title + search + add button */}
      <div className="flex items-center gap-4">
        <button
          type="button"
          onClick={() => navigate("/admin/cards")}
          className="h-8 w-8 rounded-full border border-std-border bg-white flex items-center justify-center hover:bg-std-surface-2 transition-colors shrink-0"
          aria-label="Назад к карточкам"
        >
          <ArrowLeft className="h-4 w-4 text-std-muted-fg" />
        </button>
        <h1 className="text-xl font-semibold">Шаблоны</h1>
        <div className="flex-1" />
        <div className="relative w-[340px]">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
          <Input
            placeholder="Поиск"
            value={searchRaw}
            onChange={(e) => handleSearchChange(e.target.value)}
            className="pl-9"
          />
        </div>
        <Button onClick={() => setCreateOpen(true)}>
          Добавить
          <Plus className="size-4" />
        </Button>
      </div>

      {isLoading ? (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          {Array.from({ length: 4 }).map((_, i) => (
            <Skeleton key={i} className="h-40" />
          ))}
        </div>
      ) : !filteredTemplates.length ? (
        <div className="flex flex-col items-center justify-center py-20 text-center">
          <LayoutTemplate className="h-12 w-12 text-muted-foreground mb-4" />
          <h3 className="font-semibold">
            {searchQuery ? "Ничего не найдено" : "Шаблонов пока нет"}
          </h3>
          {!searchQuery && (
            <p className="text-sm text-muted-foreground mt-1">Создайте первый шаблон</p>
          )}
        </div>
      ) : (
        <>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            {pagedTemplates.map((tpl) => {
              const styles = (tpl.default_styles ?? {}) as {
                bg_kind?: string;
                bg_color?: string;
                bg_gradient?: { start: string; end: string; angle?: number };
                photo_shape?: string;
              };
              const hasGradient = styles.bg_kind === "gradient" && styles.bg_gradient;
              const hasDarkSolid =
                styles.bg_kind === "solid" &&
                styles.bg_color &&
                styles.bg_color.toLowerCase() !== "#ffffff";
              const bgStyle: React.CSSProperties = hasGradient
                ? {
                    background: `linear-gradient(${styles.bg_gradient!.angle ?? 180}deg, ${styles.bg_gradient!.start} 0%, ${styles.bg_gradient!.end} 100%)`,
                  }
                : hasDarkSolid
                  ? { background: styles.bg_color }
                  : { background: "#FFFFFF" };

              const isDarkBg = hasGradient || hasDarkSolid;
              const previewTextColor = isDarkBg ? "#FFFFFF" : "#1F1E5E";
              const photoBg = isDarkBg ? "rgba(255,255,255,0.22)" : "rgba(31,30,94,0.08)";
              const photoBorder = isDarkBg
                ? "1px solid rgba(255,255,255,0.35)"
                : "1px solid rgba(31,30,94,0.12)";

              return (
                <div
                  key={tpl.id}
                  className="bg-white rounded-card border border-std-border overflow-hidden flex flex-col"
                >
                  {/* Card header: name + kebab menu */}
                  <div className="relative flex items-center justify-between px-4 pt-4 pb-2">
                    <h3 className="text-sm font-semibold truncate pr-2">{tpl.name}</h3>
                    <DropdownMenu>
                      <DropdownMenuTrigger asChild>
                        <button
                          className="w-11 h-11 rounded-full flex items-center justify-center hover:bg-std-surface-2 shrink-0"
                          aria-label="Действия"
                        >
                          <MoreHorizontal className="w-4 h-4 text-std-muted-fg" />
                        </button>
                      </DropdownMenuTrigger>
                      <DropdownMenuContent align="end">
                        <DropdownMenuItem
                          onClick={() => {
                            setRenameTarget({ id: tpl.id, current: tpl.name });
                            setRenameValue(tpl.name);
                          }}
                        >
                          <Pencil className="mr-2 h-4 w-4" />
                          Переименовать
                        </DropdownMenuItem>
                        <DropdownMenuItem onClick={() => navigate(`/admin/cards/new?template_id=${tpl.id}`)}>
                          <Plus className="mr-2 h-4 w-4" />
                          Создать удостоверение
                        </DropdownMenuItem>
                        <DropdownMenuItem onClick={() => navigate(`/admin/import?template_id=${tpl.id}`)}>
                          <Upload className="mr-2 h-4 w-4" />
                          Загрузить данные Excel
                        </DropdownMenuItem>
                        <DropdownMenuItem onClick={handleDownloadTemplate}>
                          <Download className="mr-2 h-4 w-4" />
                          Скачать шаблон таблицы Excel
                        </DropdownMenuItem>
                        <DropdownMenuItem
                          onClick={() => navigate(`/admin/templates/${tpl.id}/edit`)}
                        >
                          <Edit className="mr-2 h-4 w-4" />
                          Редактировать
                        </DropdownMenuItem>
                        <DropdownMenuItem onClick={() => duplicateMutation.mutate(tpl.id)}>
                          <Copy className="mr-2 h-4 w-4" />
                          Дублировать
                        </DropdownMenuItem>
                        {!tpl.is_default && (
                          <>
                            <DropdownMenuSeparator />
                            <DropdownMenuItem
                              className="text-destructive focus:text-destructive"
                              onClick={() => {
                                setDeleteCascade("template_only");
                                setDeleteTarget(tpl.id);
                              }}
                            >
                              <Trash2 className="mr-2 h-4 w-4" />
                              Удалить шаблон
                            </DropdownMenuItem>
                          </>
                        )}
                      </DropdownMenuContent>
                    </DropdownMenu>
                  </div>
                  {/* Card preview area */}
                  <div
                    className="flex flex-col items-center justify-between gap-2 pt-5 pb-5 px-4 flex-1 min-h-[210px]"
                    style={bgStyle}
                  >
                    <p className="text-caption font-medium" style={{ color: previewTextColor, opacity: 0.85 }}>
                      Членский билет №XXXX
                    </p>
                    <div
                      className="w-[96px] h-[96px] flex items-center justify-center rounded-2xl"
                      style={{
                        background: photoBg,
                        border: photoBorder,
                      }}
                    >
                      <span className="text-lg font-bold" style={{ color: previewTextColor, opacity: 0.85 }}>
                        ИИ
                      </span>
                    </div>
                    <p
                      className="text-caption font-semibold text-center"
                      style={{ color: previewTextColor }}
                    >
                      Иванов Иван Иванович
                    </p>
                  </div>
                </div>
              );
            })}
          </div>

          {/* Pagination — always shown */}
          <div className="flex justify-center items-center gap-1 mt-4 text-sm text-muted-foreground">
            <Button
              variant="ghost"
              size="sm"
              disabled={safePage <= 1}
              onClick={() => setCurrentPage((p) => p - 1)}
            >
              ← Назад
            </Button>
            {Array.from({ length: Math.min(totalPages, 4) }, (_, i) => i + 1).map((pg) => (
              <Button
                key={pg}
                variant={pg === safePage ? "default" : "ghost"}
                size="sm"
                className="w-8 h-8 p-0"
                onClick={() => setCurrentPage(pg)}
              >
                {pg}
              </Button>
            ))}
            {totalPages > 5 && <span className="px-1">…</span>}
            {totalPages > 4 && (
              <Button
                variant={safePage === totalPages ? "default" : "ghost"}
                size="sm"
                className="w-8 h-8 p-0"
                onClick={() => setCurrentPage(totalPages)}
              >
                {totalPages}
              </Button>
            )}
            <Button
              variant="ghost"
              size="sm"
              disabled={safePage >= totalPages}
              onClick={() => setCurrentPage((p) => p + 1)}
            >
              Дальше →
            </Button>
          </div>
        </>
      )}

      <Dialog open={createOpen} onOpenChange={setCreateOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Создать шаблон</DialogTitle>
          </DialogHeader>
          <Form {...form}>
            <form onSubmit={form.handleSubmit((d) => createMutation.mutate(d))}>
              <FormField
                control={form.control}
                name="name"
                render={({ field }) => (
                  <FormItem className="mb-4">
                    <FormLabel>Название</FormLabel>
                    <FormControl>
                      <Input {...field} placeholder="Стандартный шаблон" autoFocus />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />
              <DialogFooter>
                <Button type="button" variant="outline" onClick={() => setCreateOpen(false)}>
                  Отмена
                </Button>
                <Button type="submit" disabled={!categories?.length || createMutation.isPending}>
                  Создать
                </Button>
              </DialogFooter>
            </form>
          </Form>
        </DialogContent>
      </Dialog>

      <Dialog open={!!deleteTarget} onOpenChange={(o) => !o && setDeleteTarget(null)}>
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
            <Button variant="outline" onClick={() => setDeleteTarget(null)}>
              Оставить
            </Button>
            <Button
              variant="destructive"
              disabled={deleteMutation.isPending}
              onClick={() => {
                if (deleteTarget) {
                  deleteMutation.mutate(
                    { id: deleteTarget, cascade: deleteCascade },
                    {
                      onSettled: () => setDeleteTarget(null),
                    },
                  );
                }
              }}
            >
              Удалить
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <Dialog
        open={renameTarget !== null}
        onOpenChange={(o) => {
          if (!o) {
            setRenameTarget(null);
            setRenameValue("");
          }
        }}
      >
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
            <Button
              variant="outline"
              onClick={() => {
                if (renameTarget) setRenameValue(renameTarget.current);
              }}
            >
              Сбросить изменения
            </Button>
            <Button
              disabled={
                renameMutation.isPending ||
                !renameValue.trim() ||
                renameValue.trim() === renameTarget?.current
              }
              onClick={() => {
                if (renameTarget) {
                  renameMutation.mutate({ id: renameTarget.id, name: renameValue.trim() });
                }
              }}
            >
              Сохранить
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
