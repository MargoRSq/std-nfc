import { useEffect, useState } from "react";
import { ChevronDown, Users } from "lucide-react";
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { cn } from "@/lib/utils";

export interface AgeFilterValue {
  from: string;
  to: string;
}

interface Props {
  value: AgeFilterValue | null;
  onApply: (next: AgeFilterValue | null) => void;
  className?: string;
}

const EMPTY: AgeFilterValue = { from: "", to: "" };

function summary(value: AgeFilterValue | null): string {
  if (!value || (!value.from && !value.to)) return "Возраст";
  if (value.from && value.to) return `Возраст ${value.from}–${value.to}`;
  if (value.from) return `Возраст от ${value.from}`;
  return `Возраст до ${value.to}`;
}

function sanitize(raw: string): string {
  const digits = raw.replace(/\D/g, "").slice(0, 3);
  if (!digits) return "";
  return String(Math.min(150, parseInt(digits, 10)));
}

export function AgeFilterDropdown({ value, onApply, className }: Props) {
  const [open, setOpen] = useState(false);
  const [draft, setDraft] = useState<AgeFilterValue>(value ?? EMPTY);

  useEffect(() => {
    if (open) setDraft(value ?? EMPTY);
  }, [open, value]);

  const invalid =
    !!draft.from && !!draft.to && parseInt(draft.from, 10) > parseInt(draft.to, 10);

  function handleApply() {
    if (invalid) return;
    onApply(!draft.from && !draft.to ? null : draft);
    setOpen(false);
  }

  function handleReset() {
    setDraft(EMPTY);
    onApply(null);
    setOpen(false);
  }

  const isActive = !!(value && (value.from || value.to));

  return (
    <Popover open={open} onOpenChange={setOpen}>
      <PopoverTrigger asChild>
        <button
          type="button"
          className={cn(
            "inline-flex items-center justify-between gap-2 rounded-2xl border border-std-border bg-white px-4 py-2 text-sm text-left min-w-[150px]",
            isActive && "border-std-primary text-std-primary",
            className,
          )}
        >
          <span className="flex items-center gap-2 truncate">
            <Users className="h-4 w-4 shrink-0" />
            <span className="truncate">{summary(value)}</span>
          </span>
          <ChevronDown className="h-4 w-4 shrink-0 opacity-50" />
        </button>
      </PopoverTrigger>
      <PopoverContent align="start" className="w-[280px] p-4 space-y-4">
        <div className="grid grid-cols-2 gap-3">
          <div className="min-w-0">
            <Label className="text-xs text-std-muted-fg" htmlFor="age-from">
              От, лет
            </Label>
            <Input
              id="age-from"
              inputMode="numeric"
              value={draft.from}
              onChange={(e) => setDraft((d) => ({ ...d, from: sanitize(e.target.value) }))}
              placeholder="18"
              className="mt-1"
            />
          </div>
          <div className="min-w-0">
            <Label className="text-xs text-std-muted-fg" htmlFor="age-to">
              До, лет
            </Label>
            <Input
              id="age-to"
              inputMode="numeric"
              value={draft.to}
              onChange={(e) => setDraft((d) => ({ ...d, to: sanitize(e.target.value) }))}
              placeholder="65"
              className="mt-1"
            />
          </div>
        </div>

        {invalid && (
          <p className="text-xs text-destructive">«От» не может быть больше «До»</p>
        )}

        <div className="flex gap-2 justify-between">
          <Button variant="outline" onClick={handleReset} className="flex-1">
            Сбросить
          </Button>
          <Button onClick={handleApply} disabled={invalid} className="flex-1">
            Применить
          </Button>
        </div>
      </PopoverContent>
    </Popover>
  );
}
