import { useMemo } from "react";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from "recharts";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { type DashboardData } from "@/lib/api/analytics";
import { DatePickerField } from "@/components/cards/DatePickerField";
import { format, parseISO, subDays, isAfter } from "date-fns";
import { ru } from "date-fns/locale";

type Preset = "all" | "year" | "7d" | "30d" | "month" | "custom";

interface AnalyticsChartsProps {
  data: DashboardData;
  preset: Preset;
  onPresetChange: (p: Preset) => void;
  dateFrom: string;
  dateTo: string;
  onDateChange: (from: string, to: string) => void;
  showCustomInputs: boolean;
}

export function AnalyticsCharts({
  data,
  preset,
  onPresetChange,
  dateFrom,
  dateTo,
  onDateChange,
  showCustomInputs,
}: AnalyticsChartsProps) {
  const chartData = useMemo(() => {
    const all = (data.by_day ?? []).map((d) => ({
      ...d,
      label: format(parseISO(d.day), "dd.MM", { locale: ru }),
      date: parseISO(d.day),
    }));

    if (preset === "all" || preset === "year") return all;

    const cutoff =
      preset === "7d"
        ? subDays(new Date(), 7)
        : preset === "month"
          ? new Date(new Date().getFullYear(), new Date().getMonth(), 1)
          : subDays(new Date(), 30);

    return all.filter((d) => isAfter(d.date, cutoff));
  }, [data.by_day, preset]);

  const barSize = chartData.length <= 7 ? 28 : 12;

  return (
    <Card className="bg-white rounded-xl border border-std-border-card shadow-sm">
      <CardHeader className="flex flex-row items-center justify-between pb-2 flex-wrap gap-2">
        <CardTitle className="text-lg font-semibold text-std-ink">Активность</CardTitle>
        <div className="flex items-center gap-2">
          {showCustomInputs && (
            <>
              <div className="w-36 h-9 border border-input rounded-md px-3 flex items-center text-sm">
                <DatePickerField
                  value={dateFrom}
                  onChange={(v) => onDateChange(v, dateTo)}
                  placeholder="Начало"
                />
              </div>
              <div className="w-36 h-9 border border-input rounded-md px-3 flex items-center text-sm">
                <DatePickerField
                  value={dateTo}
                  onChange={(v) => onDateChange(dateFrom, v)}
                  placeholder="Конец"
                />
              </div>
            </>
          )}
          <Select value={preset} onValueChange={(v) => onPresetChange(v as Preset)}>
            <SelectTrigger className="w-44 h-9 text-sm bg-std-surface-2 border-std-border text-std-ink hover:bg-std-surface-3 focus:ring-0 focus:ring-offset-0">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">Вся история</SelectItem>
              <SelectItem value="year">Последний год</SelectItem>
              <SelectItem value="30d">Последние 30 дней</SelectItem>
              <SelectItem value="7d">Последние 7 дней</SelectItem>
              <SelectItem value="month">Последний месяц</SelectItem>
              <SelectItem value="custom">Произвольный диапазон</SelectItem>
            </SelectContent>
          </Select>
        </div>
      </CardHeader>
      <CardContent>
        <div className="rounded-2xl border border-std-border-card bg-white p-4">
          <ResponsiveContainer width="100%" height={240}>
            <BarChart data={chartData} barSize={barSize}>
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(0,0,0,0.06)" vertical={false} />
              <XAxis
                dataKey="label"
                tick={{ fontSize: 12, fontFamily: "Manrope", fill: "rgba(0,0,0,0.7)", fontWeight: 500 }}
                tickLine={false}
                axisLine={false}
              />
              <YAxis
                tick={{ fontSize: 12, fontFamily: "Manrope", fill: "rgba(0,0,0,0.7)", fontWeight: 500 }}
                tickLine={false}
                axisLine={false}
                allowDecimals={false}
              />
              <Tooltip
                cursor={{ fill: "rgba(31,30,94,0.05)" }}
                formatter={(value: number) => [value, "Сканирований"]}
              />
              <Bar
                dataKey="count"
                fill="#A8A4D9"
                radius={[4, 4, 0, 0]}
                name="Сканирований"
              />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </CardContent>
    </Card>
  );
}
