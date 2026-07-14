import { useEffect, useRef, useState } from "react";
import {
  DndContext,
  closestCenter,
  KeyboardSensor,
  PointerSensor,
  useSensor,
  useSensors,
  type DragEndEvent,
} from "@dnd-kit/core";
import {
  arrayMove,
  SortableContext,
  sortableKeyboardCoordinates,
  useSortable,
  verticalListSortingStrategy,
} from "@dnd-kit/sortable";
import { CSS } from "@dnd-kit/utilities";
import { ChevronRight, Plus, X } from "lucide-react";
import { Input } from "@/components/ui/input";
import { Checkbox } from "@/components/ui/checkbox";
import { Label } from "@/components/ui/label";
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover";
import { cn } from "@/lib/utils";
import { formatPhoneRu } from "@/lib/cards/formatPhone";
import { RowActions } from "./RowActions";

export type ContactType =
  | "telegram"
  | "whatsapp"
  | "instagram"
  | "facebook"
  | "twitter"
  | "youtube"
  | "tiktok"
  | "snapchat"
  | "twitch"
  | "discord"
  | "linkedin"
  | "email"
  | "phone"
  | "website"
  | "vk"
  | "ok"
  | "max"
  | "notes";

export type ContactInputType = "text" | "number" | "date" | "url" | "phone" | "email";

export interface ContactBlock {
  type: ContactType | null;
  value: string;
  label?: string | null;
  is_internal?: boolean;
  is_hidden?: boolean;
  input_type?: ContactInputType;
}

interface Props {
  value: ContactBlock[];
  onChange: (next: ContactBlock[]) => void;
  internalAllowed?: boolean;
  forceInternal?: boolean;
  addButtonLabel?: string;
  onLabelClick?: (idx: number) => void;
}

interface SortableRowProps {
  id: string;
  block: ContactBlock;
  internalAllowed?: boolean;
  forceInternal?: boolean;
  onUpdate: (patch: Partial<ContactBlock>) => void;
  onRemove: () => void;
  onLabelClick?: () => void;
}

function SortableRow({
  id,
  block,
  internalAllowed,
  forceInternal,
  onUpdate,
  onRemove,
  onLabelClick,
}: SortableRowProps) {
  const { attributes, listeners, setNodeRef, transform, transition, isDragging } = useSortable({
    id,
  });
  const [collapsed, setCollapsed] = useState(false);
  const [labelOpen, setLabelOpen] = useState(false);
  const [draftLabel, setDraftLabel] = useState(block.label ?? "");

  const displayLabel = block.label?.trim() ? block.label : "Название";

  return (
    <div
      ref={setNodeRef}
      style={{ transform: CSS.Transform.toString(transform), transition }}
      className={cn(
        "flex items-stretch gap-2",
        isDragging && "opacity-50",
        block.is_hidden && "opacity-60",
      )}
    >
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

      <div className="flex-1 space-y-1.5 min-w-0">
        {onLabelClick ? (
          <button
            type="button"
            onClick={onLabelClick}
            className="inline-flex items-center gap-1 text-sm font-semibold text-std-primary hover:underline focus:outline-none"
          >
            {displayLabel}
            <ChevronRight className="h-4 w-4 text-std-primary" />
          </button>
        ) : (
          <Popover
            open={labelOpen}
            onOpenChange={(open) => {
              setLabelOpen(open);
              if (open) setDraftLabel(block.label ?? "");
            }}
          >
            <PopoverTrigger asChild>
              <button
                type="button"
                className="inline-flex items-center gap-1 text-sm font-semibold text-std-primary hover:underline focus:outline-none"
              >
                {displayLabel}
                <ChevronRight className="h-4 w-4 text-std-primary" />
              </button>
            </PopoverTrigger>
            <PopoverContent align="start" className="w-64 p-3">
              <Label className="text-xs text-std-muted-fg">Название поля</Label>
              <Input
                autoFocus
                value={draftLabel}
                placeholder="Например, Телефон"
                onChange={(e) => setDraftLabel(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === "Enter") {
                    onUpdate({ label: draftLabel });
                    setLabelOpen(false);
                  }
                  if (e.key === "Escape") setLabelOpen(false);
                }}
                className="mt-1 h-9 text-sm"
              />
              <div className="mt-3 flex justify-end gap-2">
                <button
                  type="button"
                  onClick={() => setLabelOpen(false)}
                  className="text-sm text-std-muted-fg hover:text-std-ink"
                >
                  Отмена
                </button>
                <button
                  type="button"
                  onClick={() => {
                    onUpdate({ label: draftLabel });
                    setLabelOpen(false);
                  }}
                  className="text-sm font-semibold text-std-primary"
                >
                  Сохранить
                </button>
              </div>
            </PopoverContent>
          </Popover>
        )}

        <div className="relative rounded-xl bg-white px-4 py-3">
          <Input
            value={block.value}
            onChange={(e) =>
              onUpdate({
                value:
                  block.input_type === "phone"
                    ? formatPhoneRu(e.target.value)
                    : e.target.value,
              })
            }
            placeholder={
              block.input_type === "phone" ? "+7 (___) ___-__-__" : "Введите значение"
            }
            type={
              block.input_type === "date"
                ? "date"
                : block.input_type === "number"
                  ? "number"
                  : block.input_type === "email"
                    ? "email"
                    : block.input_type === "phone"
                      ? "tel"
                      : block.input_type === "url"
                        ? "url"
                        : "text"
            }
            inputMode={block.input_type === "phone" ? "tel" : undefined}
            className="w-full border-0 bg-transparent shadow-none px-0 pr-7 h-7 text-base focus-visible:ring-0"
          />
          {block.value && (
            <button
              type="button"
              aria-label="Очистить"
              onClick={() => onUpdate({ value: "" })}
              className="absolute right-4 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground"
            >
              <X className="h-4 w-4" />
            </button>
          )}
        </div>

        {internalAllowed && !forceInternal && (
          <div className="flex items-center gap-1 px-1">
            <Checkbox
              id={`internal-${id}`}
              checked={!!block.is_internal}
              onCheckedChange={(v) => onUpdate({ is_internal: !!v })}
            />
            <Label htmlFor={`internal-${id}`} className="cursor-pointer text-xs whitespace-nowrap">
              Только для админов
            </Label>
          </div>
        )}

        <RowActions
          onDelete={onRemove}
          onToggleCollapse={() => setCollapsed((c) => !c)}
          collapsed={collapsed}
          onToggleHidden={() => onUpdate({ is_hidden: !block.is_hidden })}
          hidden={block.is_hidden}
        />
      </div>
    </div>
  );
}

export function ContactBlocksEditor({
  value,
  onChange,
  internalAllowed,
  forceInternal,
  addButtonLabel = "Добавить контакт",
  onLabelClick,
}: Props) {
  const [idCounter, setIdCounter] = useState(0);
  const [ids, setIds] = useState<string[]>(() => value.map((_, i) => `cb-${i}`));
  const prevLenRef = useRef(value.length);

  useEffect(() => {
    const prev = prevLenRef.current;
    prevLenRef.current = value.length;
    if (value.length > ids.length) {
      setIds((cur) => {
        const next = [...cur];
        for (let i = cur.length; i < value.length; i++) next.push(`cb-auto-${i}-${Date.now()}`);
        return next;
      });
    } else if (value.length < prev && value.length < ids.length) {
      setIds((cur) => cur.slice(0, value.length));
    }
  }, [value.length, ids.length]);

  const sensors = useSensors(
    useSensor(PointerSensor),
    useSensor(KeyboardSensor, { coordinateGetter: sortableKeyboardCoordinates }),
  );

  function addContact() {
    const newId = `cb-${idCounter + value.length}`;
    setIdCounter((c) => c + 1);
    setIds((prev) => [...prev, newId]);
    onChange([
      ...value,
      {
        type: null,
        value: "",
        label: "",
        ...(forceInternal ? { is_internal: true } : {}),
      },
    ]);
  }

  function updateAt(idx: number, patch: Partial<ContactBlock>) {
    const next = value.map((b, i) => (i === idx ? { ...b, ...patch } : b));
    onChange(next);
  }

  function removeAt(idx: number) {
    setIds((prev) => prev.filter((_, i) => i !== idx));
    onChange(value.filter((_, i) => i !== idx));
  }

  function handleDragEnd(event: DragEndEvent) {
    const { active, over } = event;
    if (!over || active.id === over.id) return;
    const oldIdx = ids.indexOf(String(active.id));
    const newIdx = ids.indexOf(String(over.id));
    const nextIds = arrayMove(ids, oldIdx, newIdx);
    setIds(nextIds);
    onChange(arrayMove(value, oldIdx, newIdx));
  }

  return (
    <div className="space-y-2">
      <DndContext sensors={sensors} collisionDetection={closestCenter} onDragEnd={handleDragEnd}>
        <SortableContext items={ids} strategy={verticalListSortingStrategy}>
          {value.map((block, idx) => (
            <SortableRow
              key={ids[idx] ?? idx}
              id={ids[idx] ?? String(idx)}
              block={block}
              internalAllowed={internalAllowed}
              forceInternal={forceInternal}
              onUpdate={(patch) => updateAt(idx, patch)}
              onRemove={() => removeAt(idx)}
              onLabelClick={onLabelClick ? () => onLabelClick(idx) : undefined}
            />
          ))}
        </SortableContext>
      </DndContext>

      {value.length > 0 && <div className="h-px bg-std-border my-3" />}
      <button
        type="button"
        onClick={addContact}
        className="flex h-12 w-full items-center justify-start gap-2 rounded-xl border border-std-border bg-white px-5 text-sm font-semibold text-std-primary transition-colors hover:bg-std-surface-2"
      >
        <Plus className="h-5 w-5" />
        {addButtonLabel}
      </button>
    </div>
  );
}
