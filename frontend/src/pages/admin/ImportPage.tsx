import { useCallback, useEffect, useReducer, useRef, useState } from "react";
import { useDropzone } from "react-dropzone";
import { useNavigate, useSearchParams } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { toast } from "sonner";
import {
  Upload,
  Download,
  CheckCircle2,
  XCircle,
  Loader2,
  Plus,
  Search,
  ChevronRight,
  MoreHorizontal,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Progress } from "@/components/ui/progress";
import { Badge } from "@/components/ui/badge";
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuTrigger } from "@/components/ui/dropdown-menu";
import { Skeleton } from "@/components/ui/skeleton";
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { importsApi, type ImportJob } from "@/lib/api/imports";
import { templatesApi, type Template } from "@/lib/api/templates";
import { cardsApi, type Category, type CardListItem } from "@/lib/api/cards";
import { useAuthStore } from "@/stores/authStore";
import { useDebounce } from "@/hooks/useDebounce";
import { cn } from "@/lib/utils";

type WizardStep = "upload" | "processing" | "done" | "error";

interface ImportState {
  step: WizardStep;
  file: File | null;
  job: ImportJob | null;
}

type ImportAction =
  | { type: "SET_FILE"; file: File }
  | { type: "CLEAR_FILE" }
  | { type: "JOB_STARTED"; job: ImportJob }
  | { type: "JOB_UPDATED"; job: ImportJob }
  | { type: "RESET" };

function importReducer(state: ImportState, action: ImportAction): ImportState {
  switch (action.type) {
    case "SET_FILE":
      return { ...state, file: action.file };
    case "CLEAR_FILE":
      return { ...state, file: null };
    case "JOB_STARTED":
      return { ...state, step: "processing", job: action.job };
    case "JOB_UPDATED":
      if (action.job.status === "succeeded") return { ...state, step: "done", job: action.job };
      if (action.job.status === "failed" || action.job.status === "cancelled")
        return { ...state, step: "error", job: action.job };
      return { ...state, job: action.job };
    case "RESET":
      return { step: "upload", file: null, job: null };
    default:
      return state;
  }
}

type ViewMode = "grid" | "list";

const SORT_OPTIONS = [
  { label: "По дате добавления", value: "-created_at" },
  { label: "По дате изменения", value: "-updated_at" },
  { label: "Сначала старые", value: "created_at" },
  { label: "А → Я", value: "last_name" },
  { label: "Я → А", value: "-last_name" },
];

function getInitials(last: string, first: string): string {
  return `${(last || "").charAt(0)}${(first || "").charAt(0)}`.toUpperCase();
}

interface MemberTextCardProps {
  card: CardListItem;
  onClick: () => void;
}

function MemberTextCard({ card, onClick }: MemberTextCardProps) {
  const fullName = [card.last_name, card.first_name, card.middle_name]
    .filter(Boolean)
    .join(" ");
  const year = new Date(card.created_at).getFullYear();

  return (
    <div
      role="button"
      tabIndex={0}
      onClick={onClick}
      onKeyDown={(e) => {
        if (e.key === "Enter" || e.key === " ") {
          e.preventDefault();
          onClick();
        }
      }}
      className="bg-white rounded-2xl border border-std-border p-4 flex flex-col gap-2 cursor-pointer hover:shadow-sm transition-shadow relative"
    >
      <p className="text-xs font-medium text-std-muted-fg leading-tight">
        №{card.membership_no} с {year} г.
      </p>
      <p className="text-sm font-semibold text-std-ink-strong truncate leading-snug">
        {fullName}
      </p>
      <p className="text-xs text-std-ink-strong pt-1">
        Членский билет №{card.membership_no}
      </p>
    </div>
  );
}

interface TemplateTileProps {
  template: Template;
  onEdit: () => void;
}

function TemplateTile({ template, onEdit }: TemplateTileProps) {
  const styles = (template.default_styles ?? {}) as {
    bg_kind?: string;
    bg_color?: string;
    bg_gradient?: { start?: string; from?: string; end?: string; to?: string; angle?: number };
    photo_shape?: string;
  };

  const bgStyle: React.CSSProperties =
    styles.bg_kind === "gradient" && styles.bg_gradient
      ? {
          background: `linear-gradient(${styles.bg_gradient.angle ?? 180}deg, ${styles.bg_gradient.start ?? styles.bg_gradient.from ?? "#1F1E5E"} 0%, ${styles.bg_gradient.end ?? styles.bg_gradient.to ?? "#798BFF"} 100%)`,
        }
      : styles.bg_kind === "solid" && styles.bg_color
        ? { background: styles.bg_color }
        : { background: "linear-gradient(180deg, #1F1E5E 0%, #798BFF 100%)" };

  const isLightBg = styles.bg_kind === "solid" && styles.bg_color === "#FFFFFF";
  const textColor = isLightBg ? "#1F1E5E" : "#FFFFFF";
  const avatarBg = isLightBg ? "rgba(31,30,94,0.08)" : "rgba(255,255,255,0.15)";

  return (
    <div className="bg-white rounded-2xl border border-std-border overflow-hidden flex flex-col">
      <div className="px-3 pt-3 pb-2 flex items-center justify-between">
        <p className="text-sm font-semibold text-std-ink-strong truncate">{template.name}</p>
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <button
              type="button"
              className="shrink-0 w-8 h-8 flex items-center justify-center rounded-full hover:bg-std-surface-2 transition-colors"
              aria-label="Действия"
            >
              <MoreHorizontal className="h-4 w-4 text-std-muted-fg" />
            </button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end">
            <DropdownMenuItem onClick={onEdit}>Редактировать</DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      </div>

      <div
        className="flex flex-col items-center justify-center gap-2 py-6 px-3 flex-1"
        style={{ minHeight: 180, ...bgStyle }}
      >
        <p className="text-xs font-medium" style={{ color: textColor, opacity: 0.85 }}>
          Членский билет №XXXX
        </p>
        <div
          className="w-[52px] h-[52px] flex items-center justify-center rounded-2xl"
          style={{ background: avatarBg }}
        >
          <span className="text-lg font-bold" style={{ color: textColor }}>ИИ</span>
        </div>
        <p className="text-xs font-semibold text-center" style={{ color: textColor }}>
          Иванов Иван Иванович
        </p>
      </div>
    </div>
  );
}

function ImportWizardModal({
  open,
  onClose,
  templates,
}: {
  open: boolean;
  onClose: () => void;
  templates: Template[];
}) {
  const [state, dispatch] = useReducer(importReducer, {
    step: "upload",
    file: null,
    job: null,
  });

  const [selectedTemplateId, setSelectedTemplateId] = useState<string | null>(null);
  const [templateQuery, setTemplateQuery] = useState("");
  const pollingRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const clearPolling = () => {
    if (pollingRef.current) {
      clearInterval(pollingRef.current);
      pollingRef.current = null;
    }
  };

  useEffect(() => {
    if (state.step === "processing" && state.job) {
      pollingRef.current = setInterval(async () => {
        try {
          const res = await importsApi.getJob(state.job!.id);
          dispatch({ type: "JOB_UPDATED", job: res.data });
          if (
            res.data.status === "succeeded" ||
            res.data.status === "failed" ||
            res.data.status === "cancelled"
          ) {
            clearPolling();
          }
        } catch {
          clearPolling();
        }
      }, 2000);
    }
    return clearPolling;
  }, [state.step, state.job?.id]);

  const onDrop = useCallback((files: File[]) => {
    const f = files[0];
    if (f) dispatch({ type: "SET_FILE", file: f });
  }, []);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: { "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": [".xlsx"] },
    maxFiles: 1,
    noClick: !!state.file,
    noDrag: !!state.file,
  });

  const handleUpload = async () => {
    if (!state.file || !selectedTemplateId) return;
    try {
      const res = await importsApi.uploadExcel(state.file, selectedTemplateId);
      dispatch({ type: "JOB_STARTED", job: res.data });
      toast.success("Файл загружен, начинаем обработку...");
    } catch {
      toast.error("Ошибка загрузки файла");
    }
  };

  const filteredTemplates = templates.filter((t) =>
    t.name.toLowerCase().includes(templateQuery.toLowerCase()),
  );

  const progress = state.job
    ? state.job.total_rows > 0
      ? Math.round((state.job.processed_rows / state.job.total_rows) * 100)
      : 0
    : 0;

  function handleClose() {
    dispatch({ type: "RESET" });
    setSelectedTemplateId(null);
    setTemplateQuery("");
    onClose();
  }

  return (
    <Dialog open={open} onOpenChange={(v) => !v && handleClose()}>
      <DialogContent className="max-w-2xl">
        <DialogHeader>
          <DialogTitle>Загрузить данные Excel</DialogTitle>
        </DialogHeader>

        {state.step === "upload" && (
          <div className="space-y-4">
            <div
              {...getRootProps()}
              className={cn(
                "h-24 border-2 border-dashed rounded-xl px-4 text-center cursor-pointer transition-colors flex items-center justify-center gap-2",
                isDragActive
                  ? "border-primary bg-primary/5"
                  : state.file
                    ? "border-green-400 bg-green-50"
                    : "border-muted-foreground/30 hover:border-primary hover:bg-muted/30",
              )}
            >
              <input {...getInputProps()} />
              <Upload className="h-4 w-4 text-muted-foreground shrink-0" />
              <p className="text-sm text-muted-foreground">
                {state.file
                  ? state.file.name
                  : isDragActive
                    ? "Отпустите файл"
                    : "Перетащите .xlsx или нажмите для выбора"}
              </p>
            </div>

            <div>
              <p className="text-sm font-semibold mb-2">Выберите шаблон</p>
              <Input
                placeholder="Поиск"
                className="mb-3"
                value={templateQuery}
                onChange={(e) => setTemplateQuery(e.target.value)}
              />
              <div className="grid grid-cols-2 sm:grid-cols-3 gap-3 max-h-[240px] overflow-y-auto">
                {filteredTemplates.map((t) => {
                  const selected = selectedTemplateId === t.id;
                  return (
                    <button
                      key={t.id}
                      type="button"
                      onClick={() => setSelectedTemplateId(t.id)}
                      className={cn(
                        "rounded-xl border-2 px-3 py-2 text-left text-sm font-medium transition-colors",
                        selected
                          ? "border-std-primary bg-std-primary/5 text-std-primary"
                          : "border-std-border hover:border-std-primary text-std-ink-strong",
                      )}
                    >
                      {t.name}
                      {selected && <CheckCircle2 className="inline ml-1.5 h-4 w-4" />}
                    </button>
                  );
                })}
              </div>
            </div>

            <div className="flex justify-end gap-2 pt-2">
              <Button variant="outline" onClick={handleClose}>
                Отмена
              </Button>
              <Button
                className="rounded-full bg-std-primary px-6"
                disabled={!state.file || !selectedTemplateId}
                onClick={handleUpload}
              >
                Загрузить
              </Button>
            </div>
          </div>
        )}

        {state.step === "processing" && state.job && (
          <div className="space-y-4 py-2">
            <div className="flex items-center gap-2 text-sm font-medium">
              <Loader2 className="h-4 w-4 animate-spin text-primary" />
              Обработка... {state.job.processed_rows} из {state.job.total_rows} строк
            </div>
            <Progress value={progress} />
            <Button
              variant="outline"
              onClick={() => {
                void importsApi.cancelJob(state.job!.id);
                dispatch({ type: "RESET" });
              }}
            >
              Отменить
            </Button>
          </div>
        )}

        {state.step === "done" && state.job && (
          <div className="space-y-4 py-2">
            <div className="flex items-center gap-2 text-sm font-medium text-green-600">
              <CheckCircle2 className="h-4 w-4" />
              Импорт завершён
            </div>
            <div className="flex gap-6">
              <div>
                <p className="text-2xl font-bold text-green-600">
                  {state.job.inserted_rows}
                </p>
                <p className="text-xs text-muted-foreground">Успешно</p>
              </div>
              {state.job.error_count > 0 && (
                <div>
                  <p className="text-2xl font-bold text-destructive">{state.job.error_count}</p>
                  <p className="text-xs text-muted-foreground">Ошибок</p>
                </div>
              )}
            </div>
            {state.job.errors_sample.length > 0 && (
              <div className="max-h-40 overflow-y-auto space-y-1">
                {state.job.errors_sample.map((e, i) => (
                  <div key={i} className="flex items-start gap-2 text-sm">
                    <Badge variant="destructive" className="shrink-0">
                      Строка {e.row}
                    </Badge>
                    <span className="text-muted-foreground">{e.error}</span>
                  </div>
                ))}
              </div>
            )}
            <Button onClick={handleClose}>Закрыть</Button>
          </div>
        )}

        {state.step === "error" && (
          <div className="space-y-4 py-2">
            <div className="flex items-center gap-2 text-sm font-medium text-destructive">
              <XCircle className="h-4 w-4" />
              Ошибка импорта
            </div>
            <div className="flex gap-2">
              <Button onClick={() => dispatch({ type: "RESET" })} variant="outline">
                Попробовать снова
              </Button>
              <Button onClick={handleClose} variant="ghost">
                Закрыть
              </Button>
            </div>
          </div>
        )}
      </DialogContent>
    </Dialog>
  );
}

export function ImportPage() {
  const navigate = useNavigate();
  const userRole = useAuthStore((s) => s.user?.role);
  const isSuperAdmin = userRole === "super_admin";
  const [searchParams, setSearchParams] = useSearchParams();
  const [importOpen, setImportOpen] = useState(false);
  const [templateSearch, setTemplateSearch] = useState("");
  const [memberSearch, setMemberSearch] = useState("");
  const viewParam = searchParams.get("view");
  const view: ViewMode = viewParam === "list" ? "list" : "grid";
  const page = Math.max(1, parseInt(searchParams.get("page") ?? "1", 10));
  const pageSize = 20;

  const categoryIdParam = searchParams.get("category_id");
  const sortParam = searchParams.get("sort") ?? "-created_at";
  const categoryIdFilter = categoryIdParam ? parseInt(categoryIdParam, 10) : undefined;

  const debouncedMemberSearch = useDebounce(memberSearch, 300);

  const { data: templates, isLoading: templatesLoading } = useQuery({
    queryKey: ["templates"],
    queryFn: () => templatesApi.list().then((r) => r.data),
    staleTime: 5 * 60 * 1000,
  });

  const { data: categories } = useQuery({
    queryKey: ["categories"],
    queryFn: () => cardsApi.getCategories().then((r) => r.data),
    staleTime: 5 * 60 * 1000,
  });

  const { data: cardsData, isLoading: cardsLoading } = useQuery({
    queryKey: ["cards", debouncedMemberSearch, page, pageSize, categoryIdFilter, sortParam],
    queryFn: () =>
      cardsApi
        .list({
          q: debouncedMemberSearch || undefined,
          page,
          page_size: pageSize,
          category_id: categoryIdFilter,
          sort: sortParam || undefined,
        })
        .then((r) => r.data),
  });

  const pageCount = cardsData ? Math.ceil(cardsData.total / pageSize) : 1;

  function setView(v: ViewMode) {
    setSearchParams((prev) => {
      const next = new URLSearchParams(prev);
      next.set("view", v);
      next.set("page", "1");
      return next;
    });
  }

  function setPage(updater: (p: number) => number) {
    setSearchParams((prev) => {
      const next = new URLSearchParams(prev);
      next.set("page", String(updater(page)));
      return next;
    });
  }

  function setCategoryFilter(val: string) {
    setSearchParams((prev) => {
      const next = new URLSearchParams(prev);
      if (val === "all") next.delete("category_id");
      else next.set("category_id", val);
      next.set("page", "1");
      return next;
    });
  }

  function setSortFilter(val: string) {
    setSearchParams((prev) => {
      const next = new URLSearchParams(prev);
      next.set("sort", val);
      next.set("page", "1");
      return next;
    });
  }

  function handleDownloadTemplate() {
    importsApi
      .downloadTemplate()
      .then((r) => {
        const url = URL.createObjectURL(r.data as Blob);
        const a = document.createElement("a");
        a.href = url;
        a.download = "import-template.xlsx";
        a.click();
        URL.revokeObjectURL(url);
      })
      .catch(() => toast.error("Не удалось скачать шаблон"));
  }

  function handleExportAll() {
    cardsApi
      .exportAll()
      .then((r) => {
        const url = URL.createObjectURL(r.data as Blob);
        const a = document.createElement("a");
        a.href = url;
        a.download = "cards-export.xlsx";
        a.click();
        URL.revokeObjectURL(url);
        toast.success("Файл выгрузки готов");
      })
      .catch(() => toast.error("Не удалось выгрузить данные"));
  }

  const realTemplates = templates ?? [];
  const filteredTemplates = templateSearch.trim()
    ? realTemplates.filter((t) =>
        t.name.toLowerCase().includes(templateSearch.toLowerCase()),
      )
    : realTemplates;

  const ViewToggle = (
    <Tabs value={view} onValueChange={(value) => setView(value as "list" | "grid")}>
      <TabsList className="inline-flex h-auto rounded-2xl border border-std-border bg-white p-1">
        <TabsTrigger
          value="list"
          className="px-4 py-1.5 rounded-2xl text-sm font-medium transition text-std-muted-fg hover:text-black data-[state=active]:bg-std-surface-2 data-[state=active]:text-black data-[state=active]:shadow-none"
        >
          Список
        </TabsTrigger>
        <TabsTrigger
          value="grid"
          className="px-4 py-1.5 rounded-2xl text-sm font-medium transition text-std-muted-fg hover:text-black data-[state=active]:bg-std-surface-2 data-[state=active]:text-black data-[state=active]:shadow-none"
        >
          Карточки
        </TabsTrigger>
      </TabsList>
    </Tabs>
  );

  const Pagination = (
    <div className="flex justify-center items-center gap-3 mt-6">
      <Button variant="outline" disabled={page <= 1} onClick={() => setPage((p) => p - 1)}>
        ← Назад
      </Button>
      <span className="text-sm text-muted-foreground">
        Страница {page} из {pageCount}
      </span>
      <Button
        variant="outline"
        disabled={page >= pageCount}
        onClick={() => setPage((p) => p + 1)}
      >
        Дальше →
      </Button>
    </div>
  );

  return (
    <div className="space-y-6">
      {/* Page title row */}
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">Массовая загрузка</h1>
        <div className="flex items-center gap-3">
          <Button
            variant="outline"
            className="bg-white border-std-border text-std-primary hover:bg-std-surface-2 rounded-full"
            onClick={handleDownloadTemplate}
          >
            <Download className="mr-2 h-4 w-4" />
            Скачать шаблон таблицы Excel
          </Button>
          <Button
            className="rounded-full bg-std-primary text-white hover:bg-std-primary/90"
            onClick={() => setImportOpen(true)}
          >
            <Upload className="mr-2 h-4 w-4" />
            Загрузить данные Excel
          </Button>
        </div>
      </div>

      {/* Шаблоны section */}
      <div>
        <div className="flex items-center justify-between mb-3">
          <button
            type="button"
            className="flex items-center gap-1 text-lg font-semibold text-std-ink-strong hover:opacity-75 transition-opacity"
            onClick={() => navigate("/admin/templates")}
          >
            Шаблоны
            <ChevronRight className="h-5 w-5" />
          </button>
          <div className="flex items-center gap-3">
            <div className="relative">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
              <Input
                placeholder="Поиск"
                value={templateSearch}
                onChange={(e) => setTemplateSearch(e.target.value)}
                className="pl-9 w-[200px]"
              />
            </div>
            <Button
              className="rounded-full bg-std-primary text-white hover:bg-std-primary/90"
              onClick={() => navigate("/admin/templates?create=1")}
            >
              Добавить
              <Plus className="ml-1.5 h-4 w-4" />
            </Button>
          </div>
        </div>

        {templatesLoading ? (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            {Array.from({ length: 4 }).map((_, i) => (
              <Skeleton key={i} className="h-[260px] rounded-2xl" />
            ))}
          </div>
        ) : filteredTemplates.length === 0 ? (
          <p className="text-sm text-muted-foreground py-6 text-center">
            {(templates?.length ?? 0) === 0 ? "Шаблоны не найдены" : "Ничего не найдено"}
          </p>
        ) : (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            {filteredTemplates.map((t) => (
              <TemplateTile
                key={t.id}
                template={t}
                onEdit={() => navigate("/admin/templates")}
              />
            ))}
          </div>
        )}
      </div>

      {/* Члены СТД section */}
      <div>
        <div className="flex items-center justify-between mb-3">
          <h2 className="text-lg font-semibold text-std-ink-strong">Члены СТД</h2>
          {isSuperAdmin && (
            <Button
              variant="outline"
              className="bg-white border-std-border text-std-primary hover:bg-std-surface-2 rounded-full"
              onClick={handleExportAll}
            >
              <Download className="mr-2 h-4 w-4" />
              Выгрузить данные Excel
            </Button>
          )}
        </div>

        {/* Filter row */}
        <div className="flex flex-wrap items-center gap-3 mb-4">
          {ViewToggle}

          <div className="relative flex-1 min-w-[180px] max-w-sm">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
            <Input
              placeholder="Поиск"
              value={memberSearch}
              onChange={(e) => setMemberSearch(e.target.value)}
              className="pl-9"
            />
          </div>

          {categories && categories.length > 0 && (
            <Select
              value={categoryIdFilter != null ? String(categoryIdFilter) : "all"}
              onValueChange={setCategoryFilter}
            >
              <SelectTrigger className="w-[180px]">
                <SelectValue placeholder="Все категории" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">Все категории</SelectItem>
                {categories.map((cat: Category) => (
                  <SelectItem key={cat.id} value={String(cat.id)}>
                    {cat.name_ru}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          )}

          <Select value={sortParam} onValueChange={setSortFilter}>
            <SelectTrigger className="w-[200px]">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {SORT_OPTIONS.map((o) => (
                <SelectItem key={o.value} value={o.value}>
                  {o.label}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>

          <Button
            className="rounded-full bg-std-primary text-white hover:bg-std-primary/90 ml-auto"
            onClick={() => navigate("/admin/cards/new")}
          >
            Добавить
            <Plus className="ml-1.5 h-4 w-4" />
          </Button>
        </div>

        {view === "grid" ? (
          <>
            {cardsLoading ? (
              <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
                {Array.from({ length: 8 }).map((_, i) => (
                  <Skeleton key={i} className="h-[300px] rounded-card" />
                ))}
              </div>
            ) : (cardsData?.items.length ?? 0) === 0 ? (
              <div className="py-16 text-center text-muted-foreground">
                {memberSearch ? "Ничего не найдено" : "Карточек пока нет"}
              </div>
            ) : (
              <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
                {cardsData!.items.map((card) => (
                  <MemberTextCard
                    key={card.id}
                    card={card}
                    onClick={() => navigate(`/admin/cards/${card.id}`)}
                  />
                ))}
              </div>
            )}
            {(cardsData?.items.length ?? 0) > 0 && Pagination}
          </>
        ) : (
          <>
            {cardsLoading ? (
              <div className="flex flex-col gap-3">
                {Array.from({ length: 5 }).map((_, i) => (
                  <Skeleton key={i} className="h-16 rounded-2xl" />
                ))}
              </div>
            ) : (cardsData?.items.length ?? 0) === 0 ? (
              <div className="py-16 text-center text-muted-foreground">
                {memberSearch ? "Ничего не найдено" : "Карточек пока нет"}
              </div>
            ) : (
              <div className="flex flex-col gap-2">
                {cardsData!.items.map((card) => {
                  const fullName = [card.last_name, card.first_name, card.middle_name]
                    .filter(Boolean)
                    .join(" ");
                  const year = new Date(card.created_at).getFullYear();
                  return (
                    <div
                      key={card.id}
                      className="bg-white rounded-2xl border border-std-border p-4 flex items-center gap-3 cursor-pointer hover:shadow-sm transition-shadow"
                      onClick={() => navigate(`/admin/cards/${card.id}`)}
                    >
                      <div className="w-10 h-10 rounded-full bg-std-primary flex items-center justify-center shrink-0 overflow-hidden">
                        {card.photo_key ? (
                          <img
                            src={`/api/media/${card.photo_key}`}
                            alt={fullName}
                            className="w-10 h-10 rounded-full object-cover"
                          />
                        ) : (
                          <span className="text-white text-sm font-semibold">
                            {getInitials(card.last_name, card.first_name)}
                          </span>
                        )}
                      </div>
                      <div className="flex-1 min-w-0">
                        <p className="font-semibold text-std-ink-strong text-sm truncate">{fullName}</p>
                        <p className="text-xs text-std-muted-fg truncate">
                          №{card.membership_no} с {year} г.
                        </p>
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
            {(cardsData?.items.length ?? 0) > 0 && Pagination}
          </>
        )}
      </div>

      <ImportWizardModal
        open={importOpen}
        onClose={() => setImportOpen(false)}
        templates={templates ?? []}
      />
    </div>
  );
}
