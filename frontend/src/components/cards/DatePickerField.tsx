import { useEffect, useRef, useState } from "react";
import { format, parse, isValid } from "date-fns";
import { ru } from "date-fns/locale";
import { CalendarIcon, ChevronLeft, ChevronRight, X } from "lucide-react";
import { Calendar } from "@/components/ui/calendar";
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover";
import { cn } from "@/lib/utils";

interface Props {
  value: string;
  onChange: (next: string) => void;
  placeholder?: string;
  disabled?: boolean;
  yearOnly?: boolean;
}

function maskFullDate(raw: string): string {
  const digits = raw.replace(/\D/g, "").slice(0, 8);
  if (digits.length <= 2) return digits;
  if (digits.length <= 4) return `${digits.slice(0, 2)}.${digits.slice(2)}`;
  return `${digits.slice(0, 2)}.${digits.slice(2, 4)}.${digits.slice(4)}`;
}

function maskYear(raw: string): string {
  return raw.replace(/\D/g, "").slice(0, 4);
}

function isoFromMasked(masked: string, yearOnly: boolean): string | null {
  if (yearOnly) {
    if (masked.length !== 4) return null;
    const year = parseInt(masked, 10);
    if (Number.isNaN(year) || year < 1000 || year > 9999) return null;
    return `${masked}-01-01`;
  }
  if (masked.length !== 10) return null;
  const parsed = parse(masked, "dd.MM.yyyy", new Date());
  if (!isValid(parsed)) return null;
  const year = parsed.getFullYear();
  if (year < 1900 || year > 2100) return null;
  return format(parsed, "yyyy-MM-dd");
}

function maskedFromIso(iso: string, yearOnly: boolean): string {
  if (!iso) return "";
  const parsed = parse(iso, "yyyy-MM-dd", new Date());
  if (!isValid(parsed)) return "";
  return yearOnly ? format(parsed, "yyyy") : format(parsed, "dd.MM.yyyy");
}

export function DatePickerField({
  value,
  onChange,
  placeholder = "ДД.ММ.ГГГГ",
  disabled,
  yearOnly = false,
}: Props) {
  const [open, setOpen] = useState(false);
  const [text, setText] = useState(() => maskedFromIso(value, yearOnly));
  const typingRef = useRef(false);
  const placeholderText = yearOnly ? "ГГГГ" : placeholder;

  useEffect(() => {
    if (typingRef.current) {
      typingRef.current = false;
      return;
    }
    setText(maskedFromIso(value, yearOnly));
  }, [value, yearOnly]);

  const parsedDate = value ? parse(value, "yyyy-MM-dd", new Date()) : undefined;
  const isDateValid = parsedDate && isValid(parsedDate);
  const [month, setMonth] = useState<Date>(() => (isDateValid ? parsedDate : new Date()));

  useEffect(() => {
    if (!isDateValid) return;
    setMonth((prev) =>
      prev.getFullYear() === parsedDate!.getFullYear() &&
      prev.getMonth() === parsedDate!.getMonth()
        ? prev
        : parsedDate!,
    );
  }, [value]);

  function handleInputChange(raw: string) {
    typingRef.current = true;
    const masked = yearOnly ? maskYear(raw) : maskFullDate(raw);
    setText(masked);
    const iso = isoFromMasked(masked, yearOnly);
    if (iso) {
      onChange(iso);
    } else if (masked === "") {
      onChange("");
    }
  }

  function handleClear() {
    typingRef.current = true;
    setText("");
    onChange("");
  }

  return (
    <div className="relative flex-1 min-w-0">
      <Popover open={open} onOpenChange={setOpen}>
        <div className="flex items-center gap-1 min-w-0">
          <input
            type="text"
            inputMode="numeric"
            value={text}
            placeholder={placeholderText}
            disabled={disabled}
            onChange={(e) => handleInputChange(e.target.value)}
            onFocus={() => setOpen(true)}
            onClick={() => setOpen(true)}
            className={cn(
              "flex-1 min-w-0 bg-transparent border-0 outline-none text-sm p-0 placeholder:text-muted-foreground",
              "disabled:cursor-not-allowed disabled:opacity-50",
            )}
          />
          <PopoverTrigger asChild>
            <button
              type="button"
              disabled={disabled}
              aria-label="Открыть календарь"
              onClick={(e) => {
                e.stopPropagation();
                setOpen((o) => !o);
              }}
              className="shrink-0 text-muted-foreground hover:text-foreground disabled:opacity-50"
            >
              <CalendarIcon className="h-4 w-4" />
            </button>
          </PopoverTrigger>
          {text && (
            <button
              type="button"
              aria-label="Очистить"
              onClick={handleClear}
              disabled={disabled}
              className="shrink-0 text-muted-foreground hover:text-foreground disabled:opacity-50"
            >
              <X className="h-4 w-4" />
            </button>
          )}
        </div>
        <PopoverContent
          className="w-auto p-0 rounded-2xl border-std-border"
          align="start"
          onOpenAutoFocus={(e) => e.preventDefault()}
        >
          {yearOnly ? (
            <YearPicker
              selected={isDateValid ? parsedDate.getFullYear() : undefined}
              onSelect={(y) => {
                typingRef.current = false;
                onChange(`${y}-01-01`);
                setText(String(y));
                setOpen(false);
              }}
            />
          ) : (
            <Calendar
              mode="single"
              selected={isDateValid ? parsedDate : undefined}
              onSelect={(d) => {
                if (d) {
                  typingRef.current = false;
                  const iso = format(d, "yyyy-MM-dd");
                  onChange(iso);
                  setText(format(d, "dd.MM.yyyy"));
                }
                setOpen(false);
              }}
              captionLayout="dropdown"
              startMonth={new Date(1900, 0)}
              endMonth={new Date(new Date().getFullYear() + 5, 11)}
              month={month}
              onMonthChange={setMonth}
              weekStartsOn={1}
              locale={ru}
            />
          )}
        </PopoverContent>
      </Popover>
    </div>
  );
}

const YEARS_PER_PAGE = 16;

function YearPicker({
  selected,
  onSelect,
}: {
  selected?: number;
  onSelect: (year: number) => void;
}) {
  const currentYear = new Date().getFullYear();
  const initialAnchor = selected ?? currentYear;
  const [pageStart, setPageStart] = useState(
    Math.floor(initialAnchor / YEARS_PER_PAGE) * YEARS_PER_PAGE,
  );
  const years = Array.from({ length: YEARS_PER_PAGE }, (_, i) => pageStart + i);
  const pageEnd = pageStart + YEARS_PER_PAGE - 1;

  return (
    <div className="p-3 w-[252px]">
      <div className="flex items-center justify-between mb-2">
        <button
          type="button"
          aria-label="Предыдущие годы"
          onClick={() => setPageStart(pageStart - YEARS_PER_PAGE)}
          className="h-7 w-7 inline-flex items-center justify-center rounded-md hover:bg-accent text-muted-foreground"
        >
          <ChevronLeft className="h-4 w-4" />
        </button>
        <div className="text-sm font-medium">
          {pageStart} – {pageEnd}
        </div>
        <button
          type="button"
          aria-label="Следующие годы"
          onClick={() => setPageStart(pageStart + YEARS_PER_PAGE)}
          className="h-7 w-7 inline-flex items-center justify-center rounded-md hover:bg-accent text-muted-foreground"
        >
          <ChevronRight className="h-4 w-4" />
        </button>
      </div>
      <div className="grid grid-cols-4 gap-1">
        {years.map((y) => {
          const isSelected = y === selected;
          return (
            <button
              key={y}
              type="button"
              onClick={() => onSelect(y)}
              className={cn(
                "h-9 rounded-md text-sm hover:bg-accent",
                isSelected && "bg-primary text-primary-foreground hover:bg-primary",
              )}
            >
              {y}
            </button>
          );
        })}
      </div>
    </div>
  );
}
