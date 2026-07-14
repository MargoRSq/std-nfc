import { type RegionStats } from "@/lib/api/analytics";

interface RegionsBarListProps {
  regions: RegionStats[];
  totalScans: number;
}

export function RegionsBarList({ regions, totalScans }: RegionsBarListProps) {
  const items = regions.slice(0, 5).map((c) => ({
    name: c.region || "—",
    percent: totalScans > 0 ? Math.round((c.count / totalScans) * 100) : 0,
  }));

  if (items.length === 0) {
    return <p className="text-sm text-std-muted-fg">Нет данных</p>;
  }

  return (
    <div className="space-y-2">
      {items.map((item) => (
        <div key={item.name} className="flex items-center gap-3 text-sm py-0.5">
          <span className="text-std-muted-fg w-28 shrink-0 truncate">{item.name}</span>
          <div className="h-2 rounded-pill bg-std-primary/10 flex-1 max-w-[60%]">
            <div
              className="h-full rounded-pill bg-std-primary/70"
              style={{ width: item.percent + "%" }}
            />
          </div>
          <span className="font-semibold text-std-primary ml-auto">{item.percent}%</span>
        </div>
      ))}
    </div>
  );
}
