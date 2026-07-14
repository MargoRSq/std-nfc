import { useState } from "react";
import { useSortable } from "@dnd-kit/sortable";
import { CSS } from "@dnd-kit/utilities";
import { ChevronRight } from "lucide-react";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { cn } from "@/lib/utils";
import { formatPhoneRu } from "@/lib/cards/formatPhone";
import { DatePickerField } from "./DatePickerField";
import { LabelPickerSheet } from "./LabelPickerSheet";
import { RowActions } from "./RowActions";

export interface CustomField {
  key: string;
  label: string;
  value: string;
  type: "text" | "number" | "date" | "url" | "phone" | "email";
  is_hidden?: boolean;
  multiline_label?: boolean;
  is_preset?: boolean;
}

let keyCounter = 0;
export function genFieldKey(): string {
  return `field_${++keyCounter}_${Date.now()}`;
}

interface SortableCustomFieldRowProps {
  id: string;
  field: CustomField;
  onUpdate: (patch: Partial<CustomField>) => void;
  onRemove: () => void;
  onLabelClick?: () => void;
}

export function SortableCustomFieldRow({
  id,
  field,
  onUpdate,
  onRemove,
  onLabelClick,
}: SortableCustomFieldRowProps) {
  const { attributes, listeners, setNodeRef, transform, transition, isDragging } = useSortable({
    id,
    disabled: field.is_preset,
  });
  const [collapsed, setCollapsed] = useState(false);
  const [labelOpen, setLabelOpen] = useState(false);

  const displayLabel = field.label.trim() ? field.label : "Название";
  const inputType =
    field.type === "date"
      ? "date"
      : field.type === "number"
        ? "number"
        : field.type === "email"
          ? "email"
          : field.type === "phone"
            ? "tel"
            : field.type === "url"
              ? "url"
              : "text";

  return (
    <div
      ref={setNodeRef}
      style={{ transform: CSS.Transform.toString(transform), transition }}
      className={cn(
        "flex items-stretch gap-2",
        isDragging && "opacity-50",
        field.is_hidden && "opacity-60",
      )}
    >
      {!field.is_preset && (
        <button
          type="button"
          aria-label="Перетащить"
          className="flex w-6 shrink-0 cursor-grab touch-none items-center justify-center rounded-full border border-std-border bg-white py-2"
          {...attributes}
          {...listeners}
        >
          <span className="flex flex-col gap-1">
            <span className="block h-1.5 w-1.5 rounded-full bg-std-muted" />
            <span className="block h-1.5 w-1.5 rounded-full bg-std-muted" />
            <span className="block h-1.5 w-1.5 rounded-full bg-std-muted" />
          </span>
        </button>
      )}

      <div className="flex-1 space-y-1.5 min-w-0">
        {field.is_preset ? (
          <Label
            className={cn(
              "text-sm text-std-primary font-semibold flex items-center gap-1",
              field.multiline_label && "whitespace-normal",
            )}
          >
            {displayLabel}
            <ChevronRight className="h-4 w-4 text-std-primary" />
          </Label>
        ) : onLabelClick ? (
          <button
            type="button"
            onClick={onLabelClick}
            className="inline-flex items-center gap-1 text-sm font-semibold text-std-primary hover:underline focus:outline-none"
          >
            {displayLabel}
            <ChevronRight className="h-4 w-4 text-std-primary" />
          </button>
        ) : (
          <>
            <button
              type="button"
              onClick={() => setLabelOpen(true)}
              className="inline-flex items-center gap-1 text-sm font-semibold text-std-primary hover:underline focus:outline-none"
            >
              {displayLabel}
              <ChevronRight className="h-4 w-4 text-std-primary" />
            </button>
            <LabelPickerSheet
              open={labelOpen}
              onClose={() => setLabelOpen(false)}
              onApply={(name, type) => onUpdate({ label: name, type })}
            />
          </>
        )}

        <div className="rounded-xl bg-white px-4 py-3">
          {field.type === "date" ? (
            <DatePickerField
              value={field.value}
              onChange={(v) => onUpdate({ value: v })}
            />
          ) : (
            <Input
              value={field.value}
              onChange={(e) =>
                onUpdate({
                  value:
                    field.type === "phone"
                      ? formatPhoneRu(e.target.value)
                      : e.target.value,
                })
              }
              placeholder={field.type === "phone" ? "+7 (___) ___-__-__" : "Значение"}
              type={inputType}
              inputMode={field.type === "phone" ? "tel" : undefined}
              className="w-full border-0 bg-transparent shadow-none px-0 h-7 text-base focus-visible:ring-0"
            />
          )}
        </div>

        <RowActions
          onDelete={field.is_preset ? undefined : onRemove}
          canDelete={!field.is_preset}
          onToggleCollapse={() => setCollapsed((c) => !c)}
          collapsed={collapsed}
          onToggleHidden={() => onUpdate({ is_hidden: !field.is_hidden })}
          hidden={field.is_hidden}
        />
      </div>
    </div>
  );
}
