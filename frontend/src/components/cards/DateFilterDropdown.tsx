import { useState, useEffect } from "react";
import { Calendar, ChevronDown } from "lucide-react";
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from "@/components/ui/popover";
import { Button } from "@/components/ui/button";
import { RadioGroup, RadioGroupItem } from "@/components/ui/radio-group";
import { Label } from "@/components/ui/label";
import { cn } from "@/lib/utils";
import type { DateField } from "@/lib/api/cards";
import { DatePickerField } from "@/components/cards/DatePickerField";

const FIELD_OPTIONS: { value: DateField; label: string }[] = [
  { value: "added", label: "По дате добавления" },
  { value: "opened", label: "По дате последнего открытия" },
  { value: "modified", label: "По дате изменения" },
  { value: "created", label: "По дате создания" },
];

export interface DateFilterValue {
  field: DateField;
  from: string;
  to: string;
}

interface Props {
  value: DateFilterValue | null;
  onApply: (next: DateFilterValue | null) => void;
  className?: string;
}

const EMPTY: DateFilterValue = { field: "added", from: "", to: "" };

function summary(value: DateFilterValue | null): string {
  if (!value || (!value.from && !value.to)) {
    return "По дате добавления";
  }
  const opt = FIELD_OPTIONS.find((o) => o.value === value.field);
  return opt?.label ?? "По дате";
}

export function DateFilterDropdown({ value, onApply, className }: Props) {
  const [open, setOpen] = useState(false);
  const [draft, setDraft] = useState<DateFilterValue>(value ?? EMPTY);

  useEffect(() => {
    if (open) setDraft(value ?? EMPTY);
  }, [open, value]);

  function handleApply() {
    if (!draft.from && !draft.to) {
      onApply(null);
    } else {
      onApply(draft);
    }
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
            "inline-flex items-center justify-between gap-2 rounded-2xl border border-std-border bg-white px-4 py-2 text-sm text-left min-w-[200px]",
            isActive && "border-std-primary text-std-primary",
            className,
          )}
        >
          <span className="flex items-center gap-2 truncate">
            <Calendar className="h-4 w-4 shrink-0" />
            <span className="truncate">{summary(value)}</span>
          </span>
          <ChevronDown className="h-4 w-4 shrink-0 opacity-50" />
        </button>
      </PopoverTrigger>
      <PopoverContent align="start" className="w-[360px] p-4 space-y-4">
        <RadioGroup
          value={draft.field}
          onValueChange={(v) => setDraft((d) => ({ ...d, field: v as DateField }))}
          className="space-y-2"
        >
          {FIELD_OPTIONS.map((opt) => (
            <div key={opt.value} className="flex items-center justify-between">
              <Label
                htmlFor={`date-field-${opt.value}`}
                className="text-sm cursor-pointer flex-1"
              >
                {opt.label}
              </Label>
              <RadioGroupItem
                id={`date-field-${opt.value}`}
                value={opt.value}
              />
            </div>
          ))}
        </RadioGroup>

        <div className="grid grid-cols-2 gap-3">
          <div className="min-w-0">
            <Label className="text-xs text-std-muted-fg">Начальная дата</Label>
            <div className="mt-1 flex items-center rounded-lg border border-std-border px-3 py-2 text-sm min-w-0">
              <DatePickerField
                value={draft.from}
                onChange={(v) => setDraft((d) => ({ ...d, from: v }))}
                placeholder="ДД.ММ.ГГГГ"
              />
            </div>
          </div>
          <div className="min-w-0">
            <Label className="text-xs text-std-muted-fg">Конечная дата</Label>
            <div className="mt-1 flex items-center rounded-lg border border-std-border px-3 py-2 text-sm min-w-0">
              <DatePickerField
                value={draft.to}
                onChange={(v) => setDraft((d) => ({ ...d, to: v }))}
                placeholder="ДД.ММ.ГГГГ"
              />
            </div>
          </div>
        </div>

        <div className="flex gap-2 justify-between">
          <Button variant="outline" onClick={handleReset} className="flex-1">
            Сбросить
          </Button>
          <Button onClick={handleApply} className="flex-1">
            Применить
          </Button>
        </div>
      </PopoverContent>
    </Popover>
  );
}
