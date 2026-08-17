import { useState } from "react";
import { ChevronDown, MapPin } from "lucide-react";
import {
  Command,
  CommandEmpty,
  CommandGroup,
  CommandInput,
  CommandItem,
  CommandList,
} from "@/components/ui/command";
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover";
import { cn } from "@/lib/utils";
import type { RegionOption } from "@/lib/api/cards";

interface Props {
  value: string | null;
  options: RegionOption[];
  onApply: (next: string | null) => void;
  className?: string;
}

export function RegionFilterDropdown({ value, options, onApply, className }: Props) {
  const [open, setOpen] = useState(false);

  return (
    <Popover open={open} onOpenChange={setOpen}>
      <PopoverTrigger asChild>
        <button
          type="button"
          className={cn(
            "inline-flex items-center justify-between gap-2 rounded-2xl border border-std-border bg-white px-4 py-2 text-sm text-left min-w-[150px]",
            value && "border-std-primary text-std-primary",
            className,
          )}
        >
          <span className="flex items-center gap-2 truncate">
            <MapPin className="h-4 w-4 shrink-0" />
            <span className="truncate">{value || "Все регионы"}</span>
          </span>
          <ChevronDown className="h-4 w-4 shrink-0 opacity-50" />
        </button>
      </PopoverTrigger>
      <PopoverContent align="start" className="w-[280px] p-0">
        <Command>
          <CommandInput placeholder="Поиск региона..." />
          <CommandList>
            <CommandEmpty>Регион не найден</CommandEmpty>
            <CommandGroup>
              <CommandItem
                value="Все регионы"
                onSelect={() => {
                  onApply(null);
                  setOpen(false);
                }}
              >
                Все регионы
              </CommandItem>
              {options.map((opt) => (
                <CommandItem
                  key={opt.region}
                  value={opt.region}
                  onSelect={() => {
                    onApply(opt.region === value ? null : opt.region);
                    setOpen(false);
                  }}
                >
                  <span className="truncate">{opt.region}</span>
                  <span className="ml-auto pl-2 text-xs text-std-muted-fg">{opt.cards_count}</span>
                </CommandItem>
              ))}
            </CommandGroup>
          </CommandList>
        </Command>
      </PopoverContent>
    </Popover>
  );
}
