import { HexColorPicker } from "react-colorful";
import { ChevronDown } from "lucide-react";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover";
import { cn } from "@/lib/utils";

interface BackgroundValue {
  bg_kind: "solid" | "gradient";
  bg_color?: string;
  bg_gradient?: {
    from: string;
    to: string;
    angle: number;
  };
}

interface Props {
  value: BackgroundValue;
  onChange: (next: BackgroundValue) => void;
}

type Tab = "mono" | "gradient";

function normalizeHex(v: string): string {
  return v.startsWith("#") ? v : `#${v}`;
}

function previewStyle(value: BackgroundValue): React.CSSProperties {
  if (value.bg_kind === "gradient" && value.bg_gradient) {
    const { from, to, angle } = value.bg_gradient;
    return {
      background: `linear-gradient(${angle}deg, ${from || "#1F1E5E"}, ${to || "#798BFF"})`,
    };
  }
  return { backgroundColor: value.bg_color || "#1F1E5E" };
}

function tabFromValue(value: BackgroundValue): Tab {
  return value.bg_kind === "gradient" ? "gradient" : "mono";
}

interface CompactProps extends Props {
  compact?: boolean;
}

export function BackgroundPicker({ value, onChange, compact = false }: CompactProps) {
  const tab = tabFromValue(value);

  const solidColor = value.bg_color || "#1F1E5E";
  const gradFrom = value.bg_gradient?.from || "#1F1E5E";
  const gradTo = value.bg_gradient?.to || "#798BFF";

  function updateSolid(color: string) {
    onChange({ ...value, bg_kind: "solid", bg_color: color });
  }

  function updateGrad(patch: Partial<{ from: string; to: string; angle: number }>) {
    onChange({
      ...value,
      bg_kind: "gradient",
      bg_gradient: { from: gradFrom, to: gradTo, angle: value.bg_gradient?.angle ?? 180, ...patch },
    });
  }

  function handleTabChange(next: Tab) {
    if (next === "gradient") {
      onChange({
        ...value,
        bg_kind: "gradient",
        bg_gradient: value.bg_gradient ?? { from: solidColor, to: "#798BFF", angle: 180 },
      });
    } else {
      onChange({ ...value, bg_kind: "solid" });
    }
  }

  const tabs: { id: Tab; label: string }[] = [
    { id: "mono", label: "Монохром" },
    { id: "gradient", label: "Градиент" },
  ];

  const summaryText =
    value.bg_kind === "gradient"
      ? `${gradFrom} → ${gradTo}`
      : solidColor.toUpperCase();

  const innerPicker = (
    <div className="space-y-3">
      <div className="inline-flex w-full rounded-2xl bg-std-surface-2 p-1">
        {tabs.map(({ id, label }) => (
          <button
            key={id}
            type="button"
            className={cn(
              "flex-1 rounded-2xl px-4 py-1.5 text-sm font-medium transition-colors",
              tab === id
                ? "bg-white border border-std-border text-black shadow-sm"
                : "text-std-muted-fg hover:text-black",
            )}
            onClick={() => handleTabChange(id)}
          >
            {label}
          </button>
        ))}
      </div>

      {tab === "mono" && (
        <div className="space-y-3 pt-2">
          <HexColorPicker color={solidColor} onChange={updateSolid} style={{ width: "100%" }} />
          <div className="flex items-center gap-2">
            <Label className="shrink-0 text-xs">HEX</Label>
            <Input
              value={solidColor}
              onChange={(e) => updateSolid(normalizeHex(e.target.value))}
              className="font-mono text-xs h-8"
              maxLength={7}
            />
          </div>
        </div>
      )}

      {tab === "gradient" && (
        <div className="space-y-4 pt-2">
          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label className="text-xs">От</Label>
              <HexColorPicker
                color={gradFrom}
                onChange={(c) => updateGrad({ from: c })}
                style={{ width: "100%" }}
              />
              <Input
                value={gradFrom}
                onChange={(e) => updateGrad({ from: normalizeHex(e.target.value) })}
                className="font-mono text-xs h-8"
                maxLength={7}
              />
            </div>
            <div className="space-y-2">
              <Label className="text-xs">До</Label>
              <HexColorPicker
                color={gradTo}
                onChange={(c) => updateGrad({ to: c })}
                style={{ width: "100%" }}
              />
              <Input
                value={gradTo}
                onChange={(e) => updateGrad({ to: normalizeHex(e.target.value) })}
                className="font-mono text-xs h-8"
                maxLength={7}
              />
            </div>
          </div>
        </div>
      )}

      <div
        className="h-12 w-full rounded-md border"
        style={previewStyle(value)}
        aria-label="Предпросмотр фона"
      />
    </div>
  );

  if (!compact) {
    return innerPicker;
  }

  return (
    <Popover>
      <div className="flex items-center gap-2 rounded-md border bg-background px-3 py-2">
        <Input
          value={summaryText}
          onChange={(e) => {
            if (value.bg_kind === "solid") {
              updateSolid(normalizeHex(e.target.value));
            }
          }}
          readOnly={value.bg_kind === "gradient"}
          className="font-mono text-xs h-8 border-0 shadow-none focus-visible:ring-0 px-0 flex-1"
        />
        <div
          className="h-7 w-7 rounded-md border shrink-0"
          style={previewStyle(value)}
        />
        <PopoverTrigger asChild>
          <button
            type="button"
            className="text-muted-foreground hover:text-foreground"
            aria-label="Открыть выбор цвета"
          >
            <ChevronDown className="h-4 w-4" />
          </button>
        </PopoverTrigger>
      </div>
      <PopoverContent className="w-[360px] p-3" align="start">
        {innerPicker}
      </PopoverContent>
    </Popover>
  );
}

