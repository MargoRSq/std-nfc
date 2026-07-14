import { ArrowDownUp, ChevronDown } from "lucide-react";
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from "@/components/ui/popover";
import { RadioGroup, RadioGroupItem } from "@/components/ui/radio-group";
import { Label } from "@/components/ui/label";
import { cn } from "@/lib/utils";
import { useState } from "react";

export type SortOrder = "new_first" | "old_first" | "az" | "za";

const OPTIONS: { value: SortOrder; label: string; sortParam: string }[] = [
  { value: "new_first", label: "По дате добавления", sortParam: "-created_at" },
  { value: "old_first", label: "Сначала старые", sortParam: "created_at" },
  { value: "az", label: "А → Я", sortParam: "last_name" },
  { value: "za", label: "Я → А", sortParam: "-last_name" },
];

export function sortParamFor(order: SortOrder): string {
  return OPTIONS.find((o) => o.value === order)?.sortParam ?? "-created_at";
}

export function orderFromSortParam(sort: string | null | undefined): SortOrder {
  if (!sort) return "new_first";
  const found = OPTIONS.find((o) => o.sortParam === sort);
  return found?.value ?? "new_first";
}

interface Props {
  value: SortOrder;
  onChange: (next: SortOrder) => void;
  className?: string;
}

export function SortDropdown({ value, onChange, className }: Props) {
  const [open, setOpen] = useState(false);
  const current = OPTIONS.find((o) => o.value === value) ?? OPTIONS[0];

  return (
    <Popover open={open} onOpenChange={setOpen}>
      <PopoverTrigger asChild>
        <button
          type="button"
          className={cn(
            "inline-flex items-center justify-between gap-2 rounded-2xl border border-std-border bg-white px-4 py-2 text-sm text-left min-w-[180px]",
            value !== "new_first" && "border-std-primary text-std-primary",
            className,
          )}
        >
          <span className="flex items-center gap-2 truncate">
            <ArrowDownUp className="h-4 w-4 shrink-0" />
            <span className="truncate">{current.label}</span>
          </span>
          <ChevronDown className="h-4 w-4 shrink-0 opacity-50" />
        </button>
      </PopoverTrigger>
      <PopoverContent align="start" className="w-64 p-3">
        <RadioGroup
          value={value}
          onValueChange={(v) => {
            onChange(v as SortOrder);
            setOpen(false);
          }}
          className="space-y-1"
        >
          {OPTIONS.map((opt) => (
            <div key={opt.value} className="flex items-center justify-between py-1">
              <Label
                htmlFor={`sort-order-${opt.value}`}
                className="text-sm cursor-pointer flex-1"
              >
                {opt.label}
              </Label>
              <RadioGroupItem id={`sort-order-${opt.value}`} value={opt.value} />
            </div>
          ))}
        </RadioGroup>
      </PopoverContent>
    </Popover>
  );
}
