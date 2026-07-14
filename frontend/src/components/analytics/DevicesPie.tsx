import { PieChart, Pie, Cell, Tooltip, ResponsiveContainer } from "recharts";
import { type DeviceStats } from "@/lib/api/analytics";

const COLOR_BY_LABEL: Record<string, string> = {
  iOS: "#1F1E5E",
  Android: "#798BFF",
  Other: "#A0A0A0",
};

const FALLBACK_COLORS = ["#1F1E5E", "#798BFF", "#A0A0A0", "#2A3F60"];

const LABEL_RU: Record<string, string> = {
  iOS: "iOS",
  Android: "Android",
  Other: "Другое",
};

interface DevicesPieProps {
  devices: DeviceStats[];
}

export function DevicesPie({ devices }: DevicesPieProps) {
  const data = devices.map((d) => ({
    raw: d.device_type,
    name: LABEL_RU[d.device_type] ?? d.device_type,
    value: d.count,
  }));
  const total = data.reduce((sum, d) => sum + d.value, 0);

  if (data.length === 0) {
    return <p className="text-sm text-std-muted-fg">Нет данных</p>;
  }

  return (
    <div className="flex items-center gap-3">
      <div className="shrink-0 w-[100px] h-[100px]">
        <ResponsiveContainer width="100%" height="100%">
          <PieChart>
            <Pie
              data={data}
              cx="50%"
              cy="50%"
              innerRadius={0}
              outerRadius={46}
              paddingAngle={2}
              dataKey="value"
            >
              {data.map((d, idx) => (
                <Cell
                  key={d.raw}
                  fill={COLOR_BY_LABEL[d.raw] ?? FALLBACK_COLORS[idx % FALLBACK_COLORS.length]}
                />
              ))}
            </Pie>
            <Tooltip formatter={(value: number) => [`${value}`, ""]} />
          </PieChart>
        </ResponsiveContainer>
      </div>
      <div className="space-y-1 min-w-0 flex-1">
        {data.map((item, idx) => {
          const percent = total > 0 ? Math.round((item.value / total) * 100) : 0;
          const color =
            COLOR_BY_LABEL[item.raw] ?? FALLBACK_COLORS[idx % FALLBACK_COLORS.length];
          return (
            <div key={item.raw} className="flex items-center gap-2 text-xs">
              <span
                className="inline-block h-2 w-2 rounded-full shrink-0"
                style={{ backgroundColor: color }}
                aria-hidden="true"
              />
              <span className="text-std-muted-fg">{item.name}</span>
              <span className="font-semibold text-std-primary ml-auto pl-2">{percent}%</span>
            </div>
          );
        })}
      </div>
    </div>
  );
}
