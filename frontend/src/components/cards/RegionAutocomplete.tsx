import { useState } from "react";
import { Check, X } from "lucide-react";
import { Button } from "@/components/ui/button";
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
import { REGIONS } from "@/lib/data/regions";

interface Props {
  value?: string;
  onChange: (region: string) => void;
  placeholder?: string;
}

export function RegionAutocomplete({ value, onChange, placeholder = "Выберите регион" }: Props) {
  const [open, setOpen] = useState(false);

  return (
    <div className="relative flex-1">
    <Popover open={open} onOpenChange={setOpen}>
      <PopoverTrigger asChild>
        <Button
          variant="outline"
          role="combobox"
          aria-expanded={open}
          className="w-full justify-start font-normal h-auto border-0 bg-transparent shadow-none p-0 hover:bg-transparent pr-7"
          type="button"
        >
          <span className={cn(!value && "text-muted-foreground")}>
            {value || placeholder}
          </span>
        </Button>
      </PopoverTrigger>
      <PopoverContent className="w-[var(--radix-popover-trigger-width)] p-0" align="start">
        <Command>
          <CommandInput placeholder="Поиск региона..." />
          <CommandList>
            <CommandEmpty>Регион не найден</CommandEmpty>
            <CommandGroup>
              {REGIONS.map((region) => (
                <CommandItem
                  key={region}
                  value={region}
                  onSelect={() => {
                    onChange(region === value ? "" : region);
                    setOpen(false);
                  }}
                >
                  <Check
                    className={cn("mr-2 h-4 w-4", value === region ? "opacity-100" : "opacity-0")}
                  />
                  {region}
                </CommandItem>
              ))}
            </CommandGroup>
          </CommandList>
        </Command>
      </PopoverContent>
    </Popover>
    {value && (
      <button
        type="button"
        aria-label="Очистить"
        onClick={() => onChange("")}
        className="absolute right-0 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground"
      >
        <X className="h-4 w-4" />
      </button>
    )}
    </div>
  );
}
