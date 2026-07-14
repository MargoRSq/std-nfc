import { Fragment, lazy, Suspense, useMemo, useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { ChevronDown, Download, Loader2 } from "lucide-react";
import { Link } from "react-router-dom";
import { toast } from "sonner";
import { Card, CardContent } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { Button } from "@/components/ui/button";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { analyticsApi } from "@/lib/api/analytics";
import { RegionsBarList } from "@/components/analytics/RegionsBarList";
import { DevicesPie } from "@/components/analytics/DevicesPie";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";

const AnalyticsCharts = lazy(() =>
  import("@/components/analytics/AnalyticsCharts").then((m) => ({
    default: m.AnalyticsCharts,
  })),
);

type Preset = "all" | "year" | "7d" | "30d" | "month" | "custom";

function isoDate(d: Date): string {
  return d.toISOString().slice(0, 10);
}

function rangeForPreset(preset: Preset): { from: string; to: string } | null {
  const today = new Date();
  if (preset === "all") {
    return { from: "", to: "" };
  }
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

const KPI_CARD = "bg-white rounded-xl border border-std-border-card p-5 shadow-sm h-full";
const KPI_STAT_CARD = "bg-white rounded-xl border border-std-border-card px-5 py-4 shadow-sm";

function initials(last: string, first: string): string {
  const a = first?.[0] ?? "";
  const b = last?.[0] ?? "";
  return (a + b).toUpperCase() || "—";
}

function ExpandedUserRow({
  cardId,
  totalScans,
  dateFrom,
  dateTo,
}: {
  cardId: string;
  totalScans: number;
  dateFrom: string;
  dateTo: string;
}) {
  const { data, isLoading } = useQuery({
    queryKey: ["analytics-card", cardId, dateFrom, dateTo],
    queryFn: () =>
      analyticsApi
        .card(cardId, { from: dateFrom || undefined, to: dateTo || undefined })
        .then((r) => r.data),
  });

  const last30 = useMemo(() => {
    if (!data) return null;
    const cutoff = new Date();
    cutoff.setDate(cutoff.getDate() - 30);
    return data.by_day
      .filter((p) => new Date(p.day) >= cutoff)
      .reduce((sum, p) => sum + p.count, 0);
  }, [data]);

  return (
    <div className="grid grid-cols-1 md:grid-cols-[1fr_2fr_1fr] gap-4">
      <div className="flex flex-col gap-4">
        <div className="bg-white rounded-xl border border-std-border-card p-4">
          <p className="text-xs text-std-muted-fg mb-1">Всего сканирований</p>
          <p className="text-2xl font-bold text-std-primary">
            {totalScans.toLocaleString("ru-RU")}
          </p>
        </div>
        <div className="bg-white rounded-xl border border-std-border-card p-4">
          <p className="text-xs text-std-muted-fg mb-1">Сканирований за последний месяц</p>
          {isLoading ? (
            <Skeleton className="h-8 w-20" />
          ) : (
            <p className="text-2xl font-bold text-std-primary">
              {(last30 ?? 0).toLocaleString("ru-RU")}
            </p>
          )}
        </div>
      </div>
      <div className="bg-white rounded-xl border border-std-border-card p-4">
        <p className="text-xs text-std-muted-fg mb-2">Топ регионы сканирования</p>
        {isLoading ? (
          <Skeleton className="h-20 w-full" />
        ) : !data || data.by_region.length === 0 ? (
          <p className="text-sm text-std-muted-fg">Нет данных</p>
        ) : (
          <RegionsBarList regions={data.by_region} totalScans={data.total_scans} />
        )}
      </div>
      <div className="bg-white rounded-xl border border-std-border-card p-4">
        <p className="text-xs text-std-muted-fg mb-2">Устройства</p>
        {isLoading ? (
          <Skeleton className="h-20 w-full" />
        ) : !data || data.by_device.length === 0 ? (
          <p className="text-sm text-std-muted-fg">Нет данных</p>
        ) : (
          <DevicesPie devices={data.by_device} />
        )}
      </div>
    </div>
  );
}

export function AnalyticsPage() {
  const qc = useQueryClient();
  const [preset, setPreset] = useState<Preset>("30d");
  const initialRange = rangeForPreset("30d")!;
  const [dateFrom, setDateFrom] = useState<string>(initialRange.from);
  const [dateTo, setDateTo] = useState<string>(initialRange.to);
  const [topActivePage, setTopActivePage] = useState(1);
  const [expandedRow, setExpandedRow] = useState<string | null>(null);
  const TOP_ACTIVE_PAGE_SIZE = 10;

  const { data, isLoading } = useQuery({
    queryKey: ["analytics-dashboard", dateFrom, dateTo],
    queryFn: () =>
      analyticsApi
        .dashboard({ from: dateFrom || undefined, to: dateTo || undefined })
        .then((r) => r.data),
  });

  const { data: topActive, isLoading: topActiveLoading } = useQuery({
    queryKey: ["analytics-top-active", dateFrom, dateTo, topActivePage],
    queryFn: () =>
      analyticsApi
        .topActive({
          from: dateFrom || undefined,
          to: dateTo || undefined,
          page: topActivePage,
          page_size: TOP_ACTIVE_PAGE_SIZE,
        })
        .then((r) => r.data),
  });

  const handlePresetChange = (next: Preset) => {
    setPreset(next);
    setTopActivePage(1);
    if (next !== "custom") {
      const range = rangeForPreset(next);
      if (range) {
        setDateFrom(range.from);
        setDateTo(range.to);
        void qc.invalidateQueries({ queryKey: ["analytics-dashboard"] });
        void qc.invalidateQueries({ queryKey: ["analytics-top-active"] });
      }
    }
  };

  const handleDateChange = (from: string, to: string) => {
    setDateFrom(from);
    setDateTo(to);
    setTopActivePage(1);
    void qc.invalidateQueries({ queryKey: ["analytics-dashboard"] });
    void qc.invalidateQueries({ queryKey: ["analytics-top-active"] });
  };

  const totalPages = useMemo(() => {
    if (!topActive) return 1;
    return Math.max(1, Math.ceil(topActive.total / TOP_ACTIVE_PAGE_SIZE));
  }, [topActive]);

  const [exporting, setExporting] = useState(false);

  function handleExportReport() {
    if (exporting) return;
    setExporting(true);
    analyticsApi
      .report({ from: dateFrom || undefined, to: dateTo || undefined })
      .then((r) => {
        const url = URL.createObjectURL(r.data as Blob);
        const fromPart = dateFrom || "all";
        const toPart = dateTo || "all";
        const a = document.createElement("a");
        a.href = url;
        a.download = `analytics-${fromPart}_${toPart}.xlsx`;
        a.click();
        URL.revokeObjectURL(url);
        toast.success("Отчёт готов");
      })
      .catch(() => toast.error("Не удалось сформировать отчёт"))
      .finally(() => setExporting(false));
  }

  const pageNumbers = useMemo(() => {
    if (totalPages <= 7) return Array.from({ length: totalPages }, (_, i) => i + 1);
    const pages: (number | "…")[] = [1, 2, 3, 4];
    pages.push("…");
    pages.push(totalPages);
    return pages;
  }, [totalPages]);

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-start justify-between gap-4 flex-wrap">
        <div>
          <h1 className="text-2xl font-semibold leading-[140%] text-std-ink">Аналитика</h1>
        </div>
        <Button
          className="bg-std-primary text-white rounded-pill px-6 py-4 font-semibold text-sm gap-2 hover:bg-std-primary/90"
          onClick={handleExportReport}
          disabled={exporting}
        >
          {exporting ? <Loader2 className="h-4 w-4 animate-spin" /> : <Download className="h-4 w-4" />}
          {exporting ? "Готовим файл…" : "Скачать отчет"}
        </Button>
      </div>

      {/* KPI strip — 3-column: [stat-stack | regions | devices] */}
      <div className="grid grid-cols-1 md:grid-cols-[1fr_2fr_1fr] gap-5">
        {/* Left: two stat cards stacked */}
        <div className="flex flex-col gap-3">
          <div className={KPI_STAT_CARD}>
            <p className="text-sm font-medium text-std-muted-fg mb-1">Всего сканирований</p>
            {isLoading ? (
              <Skeleton className="h-8 w-28" />
            ) : (
              <p className="text-2xl font-semibold text-std-primary">
                {(data?.kpi.total_scans ?? 0).toLocaleString("ru-RU")}
              </p>
            )}
          </div>
          <div className={KPI_STAT_CARD}>
            <p className="text-sm font-medium text-std-muted-fg mb-1">Сканирований за последний месяц</p>
            {isLoading ? (
              <Skeleton className="h-8 w-28" />
            ) : (
              <p className="text-2xl font-semibold text-std-primary">
                {(data?.kpi.last_30d_scans ?? 0).toLocaleString("ru-RU")}
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
              regions={data?.top_regions ?? []}
              totalScans={data?.kpi.total_scans ?? 0}
            />
          )}
        </div>

        {/* Right: devices pie */}
        <div className={KPI_CARD}>
          <p className="text-sm font-medium text-std-muted-fg mb-3">Устройства</p>
          {isLoading ? (
            <Skeleton className="h-32 w-full" />
          ) : (
            <DevicesPie devices={data?.top_devices ?? []} />
          )}
        </div>
      </div>

      {/* Activity chart (period select lives inside the chart card) */}
      <Suspense fallback={<Skeleton className="h-80 w-full rounded-xl" />}>
        {data && (
          <AnalyticsCharts
            data={data}
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
      <div className="flex items-center justify-between gap-4 flex-wrap">
        <h2 className="text-lg font-semibold text-std-ink font-[Manrope]">
          Топ активных пользователей
        </h2>
        <Select value={preset} onValueChange={(v) => handlePresetChange(v as Preset)}>
          <SelectTrigger className="w-44 h-9 text-sm bg-std-surface-2 border-std-border text-std-ink hover:bg-std-surface-3 focus:ring-0 focus:ring-offset-0">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">Вся история</SelectItem>
            <SelectItem value="year">Последний год</SelectItem>
            <SelectItem value="30d">Последние 30 дней</SelectItem>
            <SelectItem value="7d">Последние 7 дней</SelectItem>
            <SelectItem value="month">Последний месяц</SelectItem>
          </SelectContent>
        </Select>
      </div>
      <Card className="bg-white rounded-xl border border-std-border-card shadow-sm">
        <CardContent className="pt-6">
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
                            <td className="py-3 pr-4 text-right text-std-ink">
                              {item.scans.toLocaleString("ru-RU")}
                            </td>
                            <td className="py-3 pr-4 text-std-muted-fg">{item.top_region ?? "—"}</td>
                            <td className="py-3 pr-4 text-std-muted-fg">{item.top_device ?? "—"}</td>
                            <td className="py-3">
                              <ChevronDown
                                className={`h-4 w-4 text-std-muted-fg transition-transform ${isExpanded ? "rotate-180" : ""}`}
                              />
                            </td>
                          </tr>
                          {isExpanded && (
                            <tr className="border-b border-std-border-row bg-std-surface-row-hover">
                              <td colSpan={6} className="px-4 py-4">
                                <ExpandedUserRow
                                  cardId={item.card_id}
                                  totalScans={item.scans}
                                  dateFrom={dateFrom}
                                  dateTo={dateTo}
                                />
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
