import { useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  useReactTable,
  getCoreRowModel,
  flexRender,
  type ColumnDef,
} from "@tanstack/react-table";
import { Plus, Search, Download, Upload, ArrowUp, ArrowDown, ArrowUpDown, ChevronRight, ExternalLink } from "lucide-react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Skeleton } from "@/components/ui/skeleton";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { CardActionMenu } from "@/components/cards/CardActionMenu";
import { AssignTemplateDialog } from "@/components/cards/AssignTemplateDialog";
import { PublishMessageModal } from "@/components/cards/PublishMessageModal";
import { DateFilterDropdown, type DateFilterValue } from "@/components/cards/DateFilterDropdown";
import { SortDropdown, sortParamFor, orderFromSortParam, type SortOrder } from "@/components/cards/SortDropdown";
import { AlertDialog, AlertDialogAction, AlertDialogCancel, AlertDialogContent, AlertDialogDescription, AlertDialogFooter, AlertDialogHeader, AlertDialogTitle } from "@/components/ui/alert-dialog";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { cardsApi, type CardListItem, type Category } from "@/lib/api/cards";
import { templatesApi, type Template } from "@/lib/api/templates";
import { importsApi } from "@/lib/api/imports";
import { useDebounce } from "@/hooks/useDebounce";
import { cn } from "@/lib/utils";
import { MemberCardTile } from "@/components/cards/MemberCardTile";
import { TemplateActionMenu } from "@/components/templates/TemplateActionMenu";
import { useAuthStore } from "@/stores/authStore";

type ViewMode = "grid" | "list";

const SORTABLE_COLUMNS: Record<string, { asc: string; desc: string }> = {
  last_name: { asc: "last_name", desc: "-last_name" },
  membership_no: { asc: "membership_no", desc: "-membership_no" },
  category_id: { asc: "category_id", desc: "-category_id" },
  birth_date: { asc: "birth_date", desc: "-birth_date" },
  region: { asc: "region", desc: "-region" },
};

function buildCategoryMap(categories: Category[]): Map<number, Category> {
  return new Map(categories.map((c) => [c.id, c]));
}

function formatBirthDate(iso?: string | null): string {
  if (!iso) return "—";
  try {
    return new Intl.DateTimeFormat("ru-RU", { day: "2-digit", month: "2-digit", year: "numeric" }).format(new Date(iso));
  } catch {
    return iso;
  }
}

function getInitials(last: string, first: string): string {
  return `${last.charAt(0)}${first.charAt(0)}`.toUpperCase();
}

function SortChevron({ columnKey, currentSort }: { columnKey: string; currentSort: string }) {
  const mapping = SORTABLE_COLUMNS[columnKey];
  if (!mapping) return null;
  if (currentSort === mapping.asc) return <ArrowUp className="inline ml-1 h-3.5 w-3.5 text-std-primary" />;
  if (currentSort === mapping.desc) return <ArrowDown className="inline ml-1 h-3.5 w-3.5 text-std-primary" />;
  return <ArrowUpDown className="inline ml-1 h-3.5 w-3.5 text-muted-foreground opacity-50" />;
}

function TemplateTilePreview({
  tpl,
  defaultCategoryId,
  onClick,
}: {
  tpl: Template;
  defaultCategoryId?: number | null;
  onClick: () => void;
}) {
  const styles = (tpl.default_styles ?? {}) as {
    bg_kind?: string;
    bg_color?: string;
    bg_gradient?: { start: string; end: string; angle?: number };
    photo_shape?: string;
  };
  const bgStyle: React.CSSProperties =
    styles.bg_kind === "gradient" && styles.bg_gradient
      ? {
          background: `linear-gradient(${styles.bg_gradient.angle ?? 180}deg, ${styles.bg_gradient.start} 0%, ${styles.bg_gradient.end} 100%)`,
        }
      : styles.bg_kind === "solid" && styles.bg_color
        ? { background: styles.bg_color }
        : { background: "linear-gradient(180deg, #1F1E5E 0%, #798BFF 100%)" };

  const isLightBg = styles.bg_kind === "solid" && styles.bg_color === "#FFFFFF";
  const previewTextColor = isLightBg ? "#1F1E5E" : "#FFFFFF";
  const photoBg = isLightBg ? "rgba(31,30,94,0.08)" : "rgba(255,255,255,0.15)";

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
      className="relative rounded-2xl border-2 border-std-border overflow-hidden flex flex-col hover:border-std-primary transition-colors text-left w-full cursor-pointer focus:outline-none focus:ring-2 focus:ring-std-primary"
    >
      <div className="flex items-center justify-between px-3 pt-3 pb-2 bg-white gap-2">
        <p className="text-xs font-semibold text-std-ink-strong truncate flex-1">{tpl.name}</p>
        <TemplateActionMenu template={tpl} defaultCategoryId={defaultCategoryId} />
      </div>
      <div
        className="flex flex-col items-center justify-center gap-3 py-6 px-3 flex-1"
        style={{ ...bgStyle, minHeight: 160 }}
      >
        <p className="text-caption font-medium" style={{ color: previewTextColor, opacity: 0.85 }}>
          Членский билет №XXXX
        </p>
        <div
          className="w-[72px] h-[72px] flex items-center justify-center"
          style={{
            background: photoBg,
            borderRadius: styles.photo_shape === "circle" ? "50%" : "10px",
          }}
        >
          <span className="text-xl font-bold" style={{ color: previewTextColor, opacity: 0.8 }}>
            ИИ
          </span>
        </div>
        <p className="text-caption font-semibold text-center" style={{ color: previewTextColor }}>
          Иванов Иван Иванович
        </p>
      </div>
    </div>
  );
}

export function CardsListPage() {
  const navigate = useNavigate();
  const qc = useQueryClient();
  const [searchParams, setSearchParams] = useSearchParams();
  const [search, setSearch] = useState("");
  const [deleteTarget, setDeleteTarget] = useState<string | null>(null);
  const [publishTarget, setPublishTarget] = useState<string | null>(null);
  const [assignTemplateTarget, setAssignTemplateTarget] = useState<string | null>(null);

  const viewParam = searchParams.get("view");
  const view: ViewMode = viewParam === "grid" ? "grid" : "list";
  const page = Math.max(1, parseInt(searchParams.get("page") ?? "1", 10));
  const pageSize = 20;

  const categoryIdParam = searchParams.get("category_id");
  const sortParam = searchParams.get("sort") ?? "-created_at";
  const categoryIdFilter = categoryIdParam ? parseInt(categoryIdParam, 10) : undefined;

  const dateFieldParam = searchParams.get("date_field");
  const dateFromParam = searchParams.get("date_from") ?? "";
  const dateToParam = searchParams.get("date_to") ?? "";
  const dateFilter: DateFilterValue | null =
    dateFieldParam && (dateFromParam || dateToParam)
      ? {
          field: dateFieldParam as DateFilterValue["field"],
          from: dateFromParam,
          to: dateToParam,
        }
      : null;

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
      if (val === "all") {
        next.delete("category_id");
      } else {
        next.set("category_id", val);
      }
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

  function handleColumnSort(columnKey: string) {
    const mapping = SORTABLE_COLUMNS[columnKey];
    if (!mapping) return;
    let nextSort: string;
    if (sortParam === mapping.asc) {
      nextSort = mapping.desc;
    } else if (sortParam === mapping.desc) {
      nextSort = "-created_at";
    } else {
      nextSort = mapping.asc;
    }
    setSortFilter(nextSort);
  }

  const debouncedSearch = useDebounce(search, 300);

  const { data: categories } = useQuery({
    queryKey: ["categories"],
    queryFn: () => cardsApi.getCategories().then((r) => r.data),
    staleTime: 5 * 60 * 1000,
  });

  const { data: templates } = useQuery({
    queryKey: ["templates"],
    queryFn: () => templatesApi.list().then((r) => r.data),
    staleTime: 5 * 60 * 1000,
  });

  const categoryMap = categories ? buildCategoryMap(categories) : new Map<number, Category>();

  const { data, isLoading } = useQuery({
    queryKey: [
      "cards",
      debouncedSearch,
      page,
      pageSize,
      categoryIdFilter,
      sortParam,
      dateFilter?.field,
      dateFilter?.from,
      dateFilter?.to,
    ],
    queryFn: () =>
      cardsApi
        .list({
          q: debouncedSearch || undefined,
          page,
          page_size: pageSize,
          category_id: categoryIdFilter,
          sort: sortParam || undefined,
          date_field: dateFilter?.field,
          date_from: dateFilter?.from || undefined,
          date_to: dateFilter?.to || undefined,
        })
        .then((r) => r.data),
  });

  const pageCount = data ? Math.ceil(data.total / pageSize) : 1;

  const deleteMutation = useMutation({
    mutationFn: (id: string) => cardsApi.delete(id),
    onSuccess: () => {
      toast.success("Карточка удалена");
      void qc.invalidateQueries({ queryKey: ["cards"] });
    },
    onError: () => toast.error("Не удалось удалить карточку"),
  });

  function handleDownloadTemplate() {
    importsApi.downloadTemplate().then((r) => {
      const url = URL.createObjectURL(r.data as Blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = "template.xlsx";
      a.click();
      URL.revokeObjectURL(url);
    }).catch(() => toast.error("Не удалось скачать шаблон"));
  }

  const userRole = useAuthStore((s) => s.user?.role);
  const isSuperAdmin = userRole === "super_admin";
  const [exporting, setExporting] = useState(false);

  function handleExportAll() {
    if (exporting) return;
    setExporting(true);
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
      .catch(() => toast.error("Не удалось выгрузить данные"))
      .finally(() => setExporting(false));
  }

  function SortableHeader({ columnKey, label }: { columnKey: string; label: string }) {
    return (
      <button
        type="button"
        className="flex items-center gap-0.5 hover:text-foreground transition-colors"
        onClick={() => handleColumnSort(columnKey)}
      >
        {label}
        <SortChevron columnKey={columnKey} currentSort={sortParam} />
      </button>
    );
  }

  const columns: ColumnDef<CardListItem>[] = [
    {
      accessorKey: "last_name",
      header: () => <SortableHeader columnKey="last_name" label="ФИО" />,
      cell: ({ row }) => {
        const { last_name, first_name, middle_name } = row.original;
        const fullName = [last_name, first_name, middle_name].filter(Boolean).join(" ");
        return (
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-full bg-std-primary flex items-center justify-center shrink-0">
              {row.original.photo_key ? (
                <img
                  src={`/api/media/${row.original.photo_key}`}
                  alt={fullName}
                  className="w-8 h-8 rounded-full object-cover"
                />
              ) : (
                <span className="text-white text-xs font-semibold">
                  {getInitials(last_name, first_name)}
                </span>
              )}
            </div>
            <span className="font-medium text-std-ink-strong">{fullName}</span>
          </div>
        );
      },
    },
    {
      accessorKey: "membership_no",
      header: () => <SortableHeader columnKey="membership_no" label="Номер билета" />,
      cell: ({ row }) => {
        const year = new Date(row.original.created_at).getFullYear();
        return (
          <span className="text-sm text-std-muted-fg">
            №{row.original.membership_no} с {year} г.
          </span>
        );
      },
    },
    {
      accessorKey: "category_id",
      header: () => <SortableHeader columnKey="category_id" label="Категория" />,
      cell: ({ row }) => {
        const cat = categoryMap.get(row.original.category_id);
        if (!cat) return <span className="text-sm text-muted-foreground">—</span>;
        return <span className="text-sm text-foreground">{cat.name_ru}</span>;
      },
    },
    {
      id: "birth_date",
      header: () => <SortableHeader columnKey="birth_date" label="Дата рождения" />,
      cell: ({ row }) => (
        <span className="text-sm text-std-muted-fg">
          {formatBirthDate((row.original as CardListItem & { birth_date?: string | null }).birth_date)}
        </span>
      ),
    },
    {
      accessorKey: "region",
      header: () => <SortableHeader columnKey="region" label="Регион" />,
      cell: ({ getValue }) => (
        <span className="text-sm text-muted-foreground truncate max-w-[140px] block">
          {(getValue() as string) ?? "—"}
        </span>
      ),
    },
    {
      id: "public_url",
      header: () => <span className="text-std-muted-fg">Ссылка</span>,
      cell: ({ row }) => {
        const slug = row.original.public_slug;
        if (!slug) return <span className="text-sm text-muted-foreground">—</span>;
        const fullUrl = `${window.location.origin}/c/${slug}`;
        const displayUrl = fullUrl.replace(/^https?:\/\//, "");
        return (
          <a
            href={`/c/${slug}`}
            target="_blank"
            rel="noopener noreferrer"
            onClick={(e) => e.stopPropagation()}
            className="inline-flex items-center gap-1 text-sm text-std-muted-fg hover:text-std-primary truncate max-w-[220px]"
            title={fullUrl}
          >
            <span className="truncate">{displayUrl}</span>
            <ExternalLink className="size-3 shrink-0" />
          </a>
        );
      },
    },
    {
      id: "actions",
      header: () => <span className="text-std-muted-fg">Действия</span>,
      cell: ({ row }) => (
        <CardActionMenu
          card={row.original}
          onDelete={(id) => setDeleteTarget(id)}
          onPublishMessage={(id) => setPublishTarget(id)}
          onAssignTemplate={(id) => setAssignTemplateTarget(id)}
        />
      ),
    },
  ];

  const table = useReactTable({
    data: data?.items ?? [],
    columns,
    getCoreRowModel: getCoreRowModel(),
    manualPagination: true,
    pageCount,
  });

  const ViewToggle = (
    <Tabs
      value={view}
      onValueChange={(value) => setView(value as "list" | "grid")}
      className="shrink-0"
    >
      <TabsList className="inline-flex h-auto rounded-pill border border-std-border bg-white p-1">
        <TabsTrigger
          value="list"
          className="px-4 py-1.5 rounded-pill text-sm font-medium transition text-std-muted-fg hover:text-black data-[state=active]:bg-std-surface-2 data-[state=active]:text-black data-[state=active]:shadow-none"
        >
          Список
        </TabsTrigger>
        <TabsTrigger
          value="grid"
          className="px-4 py-1.5 rounded-pill text-sm font-medium transition text-std-muted-fg hover:text-black data-[state=active]:bg-std-surface-2 data-[state=active]:text-black data-[state=active]:shadow-none"
        >
          Карточки
        </TabsTrigger>
      </TabsList>
    </Tabs>
  );

  function buildPageNumbers(current: number, total: number): (number | "…")[] {
    if (total <= 7) return Array.from({ length: total }, (_, i) => i + 1);
    const pages: (number | "…")[] = [1];
    if (current > 3) pages.push("…");
    for (let p = Math.max(2, current - 1); p <= Math.min(total - 1, current + 1); p++) {
      pages.push(p);
    }
    if (current < total - 2) pages.push("…");
    pages.push(total);
    return pages;
  }

  const Pagination = pageCount <= 1 ? null : (
    <div className="flex justify-center items-center gap-1 mt-6">
      <Button
        variant="ghost"
        size="sm"
        disabled={page <= 1}
        onClick={() => setPage((p) => p - 1)}
        className="text-sm text-std-muted-fg hover:text-black"
      >
        ← Назад
      </Button>
      {buildPageNumbers(page, pageCount).map((p, i) =>
        p === "…" ? (
          <span key={`ellipsis-${i}`} className="px-2 text-sm text-std-muted-fg">…</span>
        ) : (
          <Button
            key={p}
            variant="ghost"
            size="sm"
            className={cn(
              "w-8 h-8 p-0 text-sm rounded-lg",
              page === p ? "bg-std-primary text-white hover:bg-std-primary" : "text-std-muted-fg hover:text-black",
            )}
            onClick={() => setPage(() => p as number)}
          >
            {p}
          </Button>
        )
      )}
      <Button
        variant="ghost"
        size="sm"
        disabled={page >= pageCount}
        onClick={() => setPage((p) => p + 1)}
        className="text-sm text-std-muted-fg hover:text-black"
      >
        Далее →
      </Button>
    </div>
  );

  const TEMPLATE_ORDER = ["платин", "золот", "серебр", "умолчан"];
  const sortedTemplates = (templates ?? []).slice().sort((a, b) => {
    const ai = TEMPLATE_ORDER.findIndex((k) => a.name.toLowerCase().includes(k));
    const bi = TEMPLATE_ORDER.findIndex((k) => b.name.toLowerCase().includes(k));
    const ar = ai === -1 ? TEMPLATE_ORDER.length : ai;
    const br = bi === -1 ? TEMPLATE_ORDER.length : bi;
    return ar - br;
  });
  const visibleTemplates = sortedTemplates.slice(0, 4);

  return (
    <div className="space-y-4">
      <h1 className="sr-only">Карточки членов СТД</h1>
      {/* Массовая загрузка */}
      <div className="hidden md:flex items-center justify-between gap-4">
        <div>
          <span className="text-base font-semibold text-std-ink-strong">Массовая загрузка</span>
        </div>
        <div className="flex items-center gap-3 shrink-0">
          <Button
            variant="outline"
            className="bg-white border-std-border text-std-primary hover:bg-std-surface-2"
            onClick={handleDownloadTemplate}
          >
            <Download className="mr-2 h-4 w-4" />
            Скачать шаблон таблицы Excel
          </Button>
          <Button
            variant="outline"
            className="bg-white border-std-primary text-std-primary hover:bg-std-surface-2"
            onClick={() => navigate("/admin/import")}
          >
            <Upload className="mr-2 h-4 w-4" />
            Загрузить данные Excel
          </Button>
        </div>
      </div>

      {/* Шаблоны */}
      <div>
        <div className="flex items-center justify-between mb-3 gap-3">
          <button
            type="button"
            onClick={() => navigate("/admin/templates")}
            className="text-lg font-semibold text-std-ink-strong shrink-0 flex items-center gap-1 hover:opacity-75 transition-opacity"
          >
            Шаблоны
            <ChevronRight className="h-5 w-5 text-std-muted-fg" />
          </button>
          <div className="flex items-center gap-2 ml-auto">
            <div className="relative hidden sm:block">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
              <Input
                placeholder="Поиск"
                className="pl-9 w-[180px]"
                readOnly
                onClick={() => navigate("/admin/templates")}
              />
            </div>
            <Button onClick={() => navigate("/admin/templates?create=1")}>
              Добавить
              <Plus className="ml-2 h-4 w-4" />
            </Button>
          </div>
        </div>
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
          {(visibleTemplates.length > 0 ? visibleTemplates : Array.from({ length: 4 })).map((tpl, idx) =>
            tpl ? (
              <TemplateTilePreview
                key={(tpl as Template).id}
                tpl={tpl as Template}
                defaultCategoryId={categories?.[0]?.id ?? null}
                onClick={() => navigate("/admin/templates")}
              />
            ) : (
              <div key={idx} className="rounded-2xl bg-std-surface-2 h-[200px] animate-pulse" />
            )
          )}
        </div>
      </div>

      {/* Члены СТД heading + Excel export */}
      <div className="flex items-center justify-between gap-3 mt-2">
        <h2 className="text-lg font-semibold text-std-ink-strong">Члены СТД</h2>
        {isSuperAdmin && (
          <Button
            variant="outline"
            onClick={handleExportAll}
            disabled={exporting}
            className="bg-white border-std-border text-std-ink-strong hover:bg-std-surface-2 rounded-pill hidden sm:flex"
          >
            {exporting ? "Готовим файл…" : "Выгрузить данные Excel"}
            <Download className="ml-2 h-4 w-4 flex-shrink-0" />
          </Button>
        )}
      </div>

      {/* Filter row: toggle | search | category | date | Добавить */}
      <div className="flex flex-wrap items-center gap-3">
        {ViewToggle}

        <div className="relative flex-1 min-w-[160px] max-w-sm">
          <Search className="absolute left-4 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
          <Input
            placeholder="Поиск"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="pl-10 rounded-pill border-std-border bg-white"
          />
        </div>

        {categories && categories.length > 0 && (
          <Select
            value={categoryIdFilter != null ? String(categoryIdFilter) : "all"}
            onValueChange={setCategoryFilter}
          >
            <SelectTrigger className="w-[180px] rounded-pill border-std-border bg-white">
              <SelectValue placeholder="Все категории" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">Все категории</SelectItem>
              {categories.map((cat) => (
                <SelectItem key={cat.id} value={String(cat.id)}>
                  {cat.name_ru}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        )}

        <SortDropdown
          value={orderFromSortParam(sortParam)}
          onChange={(order: SortOrder) => setSortFilter(sortParamFor(order))}
          className="rounded-pill"
        />

        <DateFilterDropdown
          value={dateFilter}
          onApply={(next) => {
            setSearchParams((prev) => {
              const params = new URLSearchParams(prev);
              if (next) {
                params.set("date_field", next.field);
                if (next.from) params.set("date_from", next.from);
                else params.delete("date_from");
                if (next.to) params.set("date_to", next.to);
                else params.delete("date_to");
              } else {
                params.delete("date_field");
                params.delete("date_from");
                params.delete("date_to");
              }
              params.set("page", "1");
              return params;
            });
          }}
          className="rounded-pill"
        />

        <Button onClick={() => navigate("/admin/cards/new")} className="ml-auto rounded-pill">
          Добавить
          <Plus className="ml-2 h-4 w-4" />
        </Button>
      </div>

      {view === "grid" ? (
        <>
          {isLoading ? (
            <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
              {Array.from({ length: 8 }).map((_, i) => (
                <Skeleton key={i} className="h-[300px] rounded-card" />
              ))}
            </div>
          ) : (data?.items.length ?? 0) === 0 ? (
            <div className="py-24 text-center text-muted-foreground">
              {search ? "Ничего не найдено" : "Карточек пока нет"}
            </div>
          ) : (
            <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
              {data!.items.map((card) => (
                <MemberCardTile
                  key={card.id}
                  card={card}
                  onDelete={(id) => setDeleteTarget(id)}
                  onPublishMessage={(id) => setPublishTarget(id)}
                  onAssignTemplate={(id) => setAssignTemplateTarget(id)}
                />
              ))}
            </div>
          )}
          {Pagination}
        </>
      ) : (
        <>
          <div className="hidden md:block rounded-3xl border border-std-border-card bg-white shadow-sm overflow-hidden">
            <Table>
              <TableHeader>
                {table.getHeaderGroups().map((hg) => (
                  <TableRow key={hg.id} className="hover:bg-transparent border-b border-std-border">
                    {hg.headers.map((h) => (
                      <TableHead
                        key={h.id}
                        className="h-14 px-6 text-[13px] font-medium text-std-muted-fg bg-std-surface-3"
                      >
                        {flexRender(h.column.columnDef.header, h.getContext())}
                      </TableHead>
                    ))}
                  </TableRow>
                ))}
              </TableHeader>
              <TableBody>
                {isLoading ? (
                  Array.from({ length: 5 }).map((_, i) => (
                    <TableRow key={i}>
                      {columns.map((_, j) => (
                        <TableCell key={j}>
                          <Skeleton className="h-4 w-full" />
                        </TableCell>
                      ))}
                    </TableRow>
                  ))
                ) : table.getRowModel().rows.length === 0 ? (
                  <TableRow>
                    <TableCell colSpan={columns.length} className="text-center py-12 text-muted-foreground">
                      {search ? "Ничего не найдено" : "Карточек пока нет"}
                    </TableCell>
                  </TableRow>
                ) : (
                  (() => {
                    const groupByLetter = sortParam === "last_name" || sortParam === "-last_name";
                    let prevLetter: string | null = null;
                    return table.getRowModel().rows.flatMap((row) => {
                      const nodes: React.ReactNode[] = [];
                      if (groupByLetter) {
                        const letter = (row.original.last_name || "").charAt(0).toUpperCase();
                        if (letter && letter !== prevLetter) {
                          prevLetter = letter;
                          nodes.push(
                            <TableRow key={`letter-${letter}-${row.id}`} className="hover:bg-transparent border-b border-std-border">
                              <TableCell
                                colSpan={columns.length}
                                className="bg-std-surface-3 py-3 px-6 text-[13px] font-semibold text-std-muted-fg uppercase tracking-wide"
                              >
                                {letter}
                              </TableCell>
                            </TableRow>,
                          );
                        }
                      }
                      nodes.push(
                        <TableRow
                          key={row.id}
                          className="cursor-pointer"
                          onClick={() => navigate(`/admin/cards/${row.original.id}`)}
                        >
                          {row.getVisibleCells().map((cell) => (
                            <TableCell
                              key={cell.id}
                              className="px-6 py-3"
                              onClick={cell.column.id === "actions" ? (e) => e.stopPropagation() : undefined}
                            >
                              {flexRender(cell.column.columnDef.cell, cell.getContext())}
                            </TableCell>
                          ))}
                        </TableRow>,
                      );
                      return nodes;
                    });
                  })()
                )}
              </TableBody>
            </Table>
          </div>

          <div className="md:hidden flex flex-col gap-3">
            {isLoading ? (
              Array.from({ length: 5 }).map((_, i) => (
                <Skeleton key={i} className="h-[88px] rounded-2xl" />
              ))
            ) : (data?.items.length ?? 0) === 0 ? (
              <div className="py-16 text-center text-muted-foreground">
                {search ? "Ничего не найдено" : "Карточек пока нет"}
              </div>
            ) : (
              data!.items.map((card) => {
                const fullName = [card.last_name, card.first_name, card.middle_name].filter(Boolean).join(" ");
                const cat = categoryMap.get(card.category_id);
                const year = new Date(card.created_at).getFullYear();
                const birthDateRaw = (card as CardListItem & { birth_date?: string | null }).birth_date;
                return (
                  <div
                    key={card.id}
                    role="button"
                    tabIndex={0}
                    className="bg-white rounded-2xl border border-std-border p-4 flex gap-3 cursor-pointer active:bg-std-surface-2 transition-colors"
                    onClick={() => navigate(`/admin/cards/${card.id}`)}
                    onKeyDown={(e) => {
                      if (e.key === "Enter") navigate(`/admin/cards/${card.id}`);
                    }}
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
                      <div className="flex items-start justify-between gap-2">
                        <p className="font-semibold text-std-ink-strong text-sm truncate">{fullName}</p>
                        <CardActionMenu
                          card={card}
                          onDelete={(id) => setDeleteTarget(id)}
                          onPublishMessage={(id) => setPublishTarget(id)}
                          onAssignTemplate={(id) => setAssignTemplateTarget(id)}
                          triggerClassName="h-7 w-7 -mt-1 -mr-1 shrink-0"
                        />
                      </div>
                      <p className="text-xs text-std-muted-fg mt-1 truncate">
                        №{card.membership_no} с {year} г.
                        {cat ? <> · {cat.name_ru}</> : null}
                      </p>
                      <p className="text-xs text-std-muted-fg truncate">
                        {(card.region ?? "—")} · {formatBirthDate(birthDateRaw)}
                      </p>
                      {card.public_slug && (() => {
                        const fullUrl = `${window.location.origin}/c/${card.public_slug}`;
                        const displayUrl = fullUrl.replace(/^https?:\/\//, "");
                        return (
                          <a
                            href={`/c/${card.public_slug}`}
                            target="_blank"
                            rel="noopener noreferrer"
                            onClick={(e) => e.stopPropagation()}
                            className="inline-flex items-center gap-1 text-xs text-std-muted-fg hover:text-std-primary truncate mt-0.5"
                            title={fullUrl}
                          >
                            <span className="truncate">{displayUrl}</span>
                            <ExternalLink className="size-3 shrink-0" />
                          </a>
                        );
                      })()}
                    </div>
                  </div>
                );
              })
            )}
          </div>
          {Pagination}
        </>
      )}

      <PublishMessageModal
        cardId={publishTarget}
        open={publishTarget !== null}
        onOpenChange={(o) => {
          if (!o) setPublishTarget(null);
        }}
      />

      <AssignTemplateDialog
        open={assignTemplateTarget !== null}
        cardId={assignTemplateTarget}
        onClose={() => setAssignTemplateTarget(null)}
      />

      <AlertDialog open={!!deleteTarget} onOpenChange={(o) => !o && setDeleteTarget(null)}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Удалить карточку?</AlertDialogTitle>
            <AlertDialogDescription>
              Это действие нельзя отменить. Карточка будет удалена безвозвратно.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Отмена</AlertDialogCancel>
            <AlertDialogAction
              className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
              onClick={() => {
                if (deleteTarget) deleteMutation.mutate(deleteTarget);
                setDeleteTarget(null);
              }}
            >
              Удалить
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
}
