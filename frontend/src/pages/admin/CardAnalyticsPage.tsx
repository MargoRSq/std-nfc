import { Fragment, lazy, Suspense, useMemo, useState } from "react";
import { useParams, Link } from "react-router-dom";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { ChevronDown, Download, Loader2 } from "lucide-react";
import { parseISO, subDays, isAfter } from "date-fns";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import {
  analyticsApi,
  type CardAnalytics,
  type DashboardData,
} from "@/lib/api/analytics";
import { RegionsBarList } from "@/components/analytics/RegionsBarList";
import { DevicesPie } from "@/components/analytics/DevicesPie";

const AnalyticsCharts = lazy(() =>
  import("@/components/analytics/AnalyticsCharts").then((m) => ({
    default: m.AnalyticsCharts,
  })),
);

type Preset = "all" | "year" | "7d" | "30d" | "month" | "custom";

const KPI_CARD = "bg-white rounded-xl border border-std-border-card p-5 shadow-sm";

function isoDate(d: Date): string {
  return d.toISOString().slice(0, 10);
}

function rangeForPreset(preset: Preset): { from: string; to: string } | null {
  const today = new Date();
  if (preset === "all") return { from: "", to: "" };
  if (preset === "year") {
    const from = new Date();
    from.setDate(from.getDate() - 365);
    return { from: isoDate(from), to: isoDate(today) };
  }
  if (preset === "7d") {
    const from = new Date();
    from.setDate(from.getDate() - 7);
    return { from: isoDate(from), to: isoDate(today) };
  }
  if (preset === "30d") {
    const from = new Date();
    from.setDate(from.getDate() - 30);
    return { from: isoDate(from), to: isoDate(today) };
  }
  if (preset === "month") {
    const from = new Date(today.getFullYear(), today.getMonth(), 1);
    return { from: isoDate(from), to: isoDate(today) };
  }
  return null;
}

function initials(last: string, first: string): string {
  const a = first?.[0] ?? "";
  const b = last?.[0] ?? "";
  return (a + b).toUpperCase() || "—";
}

function adaptCardToDashboard(card: CardAnalytics): DashboardData {
  const cutoff = subDays(new Date(), 30);
  const last30 = (card.by_day ?? []).filter((d) => isAfter(parseISO(d.day), cutoff));
  const last30Scans = last30.reduce((sum, d) => sum + d.count, 0);
  return {
    kpi: {
      total_scans: card.total_scans,
      last_30d_scans: last30Scans,
      unique_cards: 1,
      active_members: 0,
    },
    by_day: card.by_day ?? [],
    top_regions: card.by_region ?? [],
    top_devices: card.by_device ?? [],
    top_cards: [],
  };
}

export function CardAnalyticsPage() {
  const { id } = useParams<{ id: string }>();
  const qc = useQueryClient();
  const [preset, setPreset] = useState<Preset>("30d");
  const initialRange = rangeForPreset("30d")!;
  const [dateFrom, setDateFrom] = useState<string>(initialRange.from);
  const [dateTo, setDateTo] = useState<string>(initialRange.to);
  const [topActivePage, setTopActivePage] = useState(1);
  const [expandedRow, setExpandedRow] = useState<string | null>(null);
  const TOP_ACTIVE_PAGE_SIZE = 10;

  const { data: card, isLoading } = useQuery({
    queryKey: ["card-analytics", id, dateFrom, dateTo],
    queryFn: () =>
      analyticsApi.card(id!, { from: dateFrom || undefined, to: dateTo || undefined }).then((r) => r.data),
    enabled: !!id,
  });

  const dashboardLike = useMemo(
    () => (card ? adaptCardToDashboard(card) : null),
    [card],
  );

  const { data: topActive, isLoading: topActiveLoading } = useQuery({
    queryKey: ["card-analytics-top-active", id, dateFrom, dateTo, topActivePage],
    queryFn: () =>
      analyticsApi
        .topActive({
          from: dateFrom || undefined,
          to: dateTo || undefined,
          page: topActivePage,
          page_size: TOP_ACTIVE_PAGE_SIZE,
        })
        .then((r) => r.data),
    enabled: !!id,
  });

  const handlePresetChange = (next: Preset) => {
    setPreset(next);
    setTopActivePage(1);
    if (next !== "custom") {
      const range = rangeForPreset(next);
      if (range) {
        setDateFrom(range.from);
        setDateTo(range.to);
        void qc.invalidateQueries({ queryKey: ["card-analytics-top-active"] });
      }
    }
  };

  const handleDateChange = (from: string, to: string) => {
    setDateFrom(from);
    setDateTo(to);
    setTopActivePage(1);
    void qc.invalidateQueries({ queryKey: ["card-analytics-top-active"] });
  };

  const totalPages = useMemo(() => {
    if (!topActive) return 1;
    return Math.max(1, Math.ceil(topActive.total / TOP_ACTIVE_PAGE_SIZE));
  }, [topActive]);

  const pageNumbers = useMemo(() => {
    if (totalPages <= 7) return Array.from({ length: totalPages }, (_, i) => i + 1);
    const pages: (number | "…")[] = [1, 2, 3, 4];
    pages.push("…");
    pages.push(totalPages);
    return pages;
  }, [totalPages]);

  const [exporting, setExporting] = useState(false);

  function handleExportReport() {
    if (!id || exporting) return;
    setExporting(true);
    analyticsApi
      .cardReport(id, { from: dateFrom || undefined, to: dateTo || undefined })
      .then((r) => {
        const url = URL.createObjectURL(r.data as Blob);
        const fromPart = dateFrom || "all";
        const toPart = dateTo || "all";
        const a = document.createElement("a");
        a.href = url;
        a.download = `card-${id}-${fromPart}_${toPart}.xlsx`;
        a.click();
        URL.revokeObjectURL(url);
        toast.success("Отчёт готов");
      })
      .catch(() => toast.error("Не удалось сформировать отчёт"))
      .finally(() => setExporting(false));
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-start justify-between gap-4 flex-wrap">
        <h1 className="text-2xl font-semibold leading-[140%] text-std-ink">Аналитика</h1>
        <Button
          className="bg-std-primary text-white rounded-pill px-6 py-4 font-semibold text-sm gap-2 disabled:opacity-50 hover:bg-std-primary/90"
          onClick={handleExportReport}
          disabled={exporting || !id}
        >
          {exporting ? <Loader2 className="h-4 w-4 animate-spin" /> : <Download className="h-4 w-4" />}
          {exporting ? "Готовим файл…" : "Скачать отчет"}
        </Button>
      </div>

      {/* KPI strip: [stat-stack | regions | devices] */}
      <div className="grid grid-cols-1 md:grid-cols-[1fr_2fr_1fr] gap-5">
        {/* Left: two stacked compact stat cards */}
        <div className="flex flex-col gap-5">
          <div className={KPI_CARD}>
            <p className="text-sm font-medium text-std-muted-fg mb-2">Всего сканирований</p>
            {isLoading ? (
              <Skeleton className="h-8 w-28" />
            ) : (
              <p className="text-2xl font-semibold text-std-primary">
                {(dashboardLike?.kpi.total_scans ?? 0).toLocaleString("ru-RU")}
              </p>
            )}
          </div>
          <div className={KPI_CARD}>
            <p className="text-sm font-medium text-std-muted-fg mb-2">
              Сканирований за последний месяц
            </p>
            {isLoading ? (
              <Skeleton className="h-8 w-28" />
            ) : (
              <p className="text-2xl font-semibold text-std-primary">
                {(dashboardLike?.kpi.last_30d_scans ?? 0).toLocaleString("ru-RU")}
              </p>
            )}
          </div>
        </div>

        {/* Center: top regions */}
        <div className={KPI_CARD}>
          <p className="text-sm font-medium text-std-muted-fg mb-3">Топ регионы сканирования</p>
          {isLoading ? (
            <div className="space-y-2">
              {[...Array(5)].map((_, i) => (
                <Skeleton key={i} className="h-6 w-full" />
              ))}
            </div>
          ) : (
            <RegionsBarList
              regions={dashboardLike?.top_regions ?? []}
              totalScans={(dashboardLike?.top_regions ?? []).reduce((s, r) => s + r.count, 0)}
            />
          )}
        </div>

        {/* Right: devices pie */}
        <div className={KPI_CARD}>
          <p className="text-sm font-medium text-std-muted-fg mb-3">Устройства</p>
          {isLoading ? (
            <Skeleton className="h-32 w-full" />
          ) : (
            <DevicesPie devices={dashboardLike?.top_devices ?? []} />
          )}
        </div>
      </div>

      {/* Activity chart */}
      <Suspense fallback={<Skeleton className="h-80 w-full rounded-xl" />}>
        {dashboardLike && (
          <AnalyticsCharts
            data={dashboardLike}
            preset={preset}
            onPresetChange={handlePresetChange}
            dateFrom={dateFrom}
            dateTo={dateTo}
            onDateChange={handleDateChange}
            showCustomInputs={preset === "custom"}
          />
        )}
      </Suspense>

      {/* Top active users table */}
      <Card className="bg-white rounded-xl border border-std-border-card shadow-sm">
        <CardHeader className="flex flex-row items-center justify-between">
          <CardTitle className="text-lg font-semibold text-std-ink font-[Manrope]">
            Топ активных пользователей
          </CardTitle>
        </CardHeader>
        <CardContent>
          {topActiveLoading ? (
            <div className="space-y-3">
              {[...Array(5)].map((_, i) => (
                <Skeleton key={i} className="h-12 w-full" />
              ))}
            </div>
          ) : !topActive || topActive.items.length === 0 ? (
            <p className="text-sm text-std-muted-fg">Нет данных за выбранный период</p>
          ) : (
            <>
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="text-left text-xs text-std-muted-fg border-b border-std-border-card">
                      <th className="py-2 pr-4 font-medium">ФИО</th>
                      <th className="py-2 pr-4 font-medium">Номер билета</th>
                      <th className="py-2 pr-4 font-medium text-right">Сканирований</th>
                      <th className="py-2 pr-4 font-medium">Топ регион</th>
                      <th className="py-2 pr-4 font-medium">Топ устройство</th>
                      <th className="py-2 font-medium">Подробности</th>
                    </tr>
                  </thead>
                  <tbody>
                    {topActive.items.map((item) => {
                      const fullName = [item.last_name, item.first_name, item.middle_name]
                        .filter(Boolean)
                        .join(" ");
                      const isExpanded = expandedRow === item.card_id;
                      return (
                        <Fragment key={item.card_id}>
                          <tr
                            className="border-b border-std-border-row cursor-pointer hover:bg-std-surface-row-hover transition-colors"
                            onClick={() => setExpandedRow(isExpanded ? null : item.card_id)}
                          >
                            <td className="py-3 pr-4">
                              <div className="flex items-center gap-3">
                                <Avatar className="h-8 w-8 shrink-0">
                                  <AvatarFallback className="bg-std-primary/10 text-std-primary text-xs font-semibold">
                                    {initials(item.last_name, item.first_name)}
                                  </AvatarFallback>
                                </Avatar>
                                <span className="font-medium text-std-ink">{fullName}</span>
                              </div>
                            </td>
                            <td className="py-3 pr-4 text-std-muted-fg">{item.membership_no}</td>
                            <td className="py-3 pr-4 text-right font-semibold text-std-ink">
                              {item.scans.toLocaleString("ru-RU")}
                            </td>
                            <td className="py-3 pr-4 text-std-muted-fg">—</td>
                            <td className="py-3 pr-4 text-std-muted-fg">—</td>
                            <td className="py-3">
                              <ChevronDown
                                className={`h-4 w-4 text-std-muted-fg transition-transform ${isExpanded ? "rotate-180" : ""}`}
                              />
                            </td>
                          </tr>
                          {isExpanded && (
                            <tr className="border-b border-std-border-row bg-std-surface-row-hover">
                              <td colSpan={6} className="px-4 py-4">
                                <div className="grid grid-cols-1 md:grid-cols-[1fr_2fr_1fr] gap-4">
                                  <div className="flex flex-col gap-4">
                                    <div className="bg-white rounded-xl border border-std-border-card p-4">
                                      <p className="text-xs text-std-muted-fg mb-1">
                                        Всего сканирований
                                      </p>
                                      <p className="text-2xl font-bold text-std-primary">
                                        {item.scans.toLocaleString("ru-RU")}
                                      </p>
                                    </div>
                                    <div className="bg-white rounded-xl border border-std-border-card p-4">
                                      <p className="text-xs text-std-muted-fg mb-1">
                                        Сканирований за последний месяц
                                      </p>
                                      <p className="text-2xl font-bold text-std-primary">—</p>
                                    </div>
                                  </div>
                                  <div className="bg-white rounded-xl border border-std-border-card p-4">
                                    <p className="text-xs text-std-muted-fg mb-2">
                                      Топ регионы сканирования
                                    </p>
                                    <p className="text-sm text-std-muted-fg">
                                      Недостаточно данных
                                    </p>
                                  </div>
                                  <div className="bg-white rounded-xl border border-std-border-card p-4">
                                    <p className="text-xs text-std-muted-fg mb-2">Устройства</p>
                                    <p className="text-sm text-std-muted-fg">
                                      Недостаточно данных
                                    </p>
                                  </div>
                                </div>
                                <div className="mt-3 flex justify-end">
                                  <Link
                                    to={`/admin/cards/${item.card_id}/analytics`}
                                    className="text-sm text-std-primary hover:underline font-medium"
                                  >
                                    Подробная аналитика →
                                  </Link>
                                </div>
                              </td>
                            </tr>
                          )}
                        </Fragment>
                      );
                    })}
                  </tbody>
                </table>
              </div>
              {totalPages > 1 && (
                <div className="flex justify-center items-center gap-1 mt-4">
                  <Button
                    variant="ghost"
                    size="sm"
                    disabled={topActivePage <= 1}
                    onClick={() => setTopActivePage((p) => Math.max(1, p - 1))}
                    className="text-std-muted-fg hover:text-std-ink"
                  >
                    ← Назад
                  </Button>
                  {pageNumbers.map((p, idx) =>
                    p === "…" ? (
                      <span key={`ellipsis-${idx}`} className="px-1 text-std-muted-fg text-sm">
                        …
                      </span>
                    ) : (
                      <Button
                        key={p}
                        variant={p === topActivePage ? "default" : "ghost"}
                        size="sm"
                        onClick={() => setTopActivePage(p as number)}
                        className={
                          p === topActivePage
                            ? "bg-std-primary text-white hover:bg-std-primary/90 h-8 w-8 p-0"
                            : "text-std-muted-fg hover:text-std-ink h-8 w-8 p-0"
                        }
                      >
                        {p}
                      </Button>
                    ),
                  )}
                  <Button
                    variant="ghost"
                    size="sm"
                    disabled={topActivePage >= totalPages}
                    onClick={() => setTopActivePage((p) => p + 1)}
                    className="text-std-muted-fg hover:text-std-ink"
                  >
                    Дальше →
                  </Button>
                </div>
              )}
            </>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
