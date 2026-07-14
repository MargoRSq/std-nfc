import type { ReactNode } from "react";
import { ChevronRight } from "lucide-react";
import { useSortable } from "@dnd-kit/sortable";
import { CSS } from "@dnd-kit/utilities";
import { cn } from "@/lib/utils";

interface SortablePresetRowProps {
  id: string;
  label: string;
  multilineLabel?: boolean;
  hidden: boolean;
  noDrag?: boolean;
  onLabelClick?: () => void;
  children: ReactNode;
}

export function SortablePresetRow({
  id,
  label,
  multilineLabel = false,
  hidden,
  noDrag = false,
  onLabelClick,
  children,
}: SortablePresetRowProps) {
  const { attributes, listeners, setNodeRef, transform, transition, isDragging } = useSortable({ id });
  return (
    <div
      ref={setNodeRef}
      style={{ transform: CSS.Transform.toString(transform), transition }}
      className={cn("flex items-stretch gap-2", isDragging && "opacity-50")}
    >
      {!noDrag && (
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
      <div className={cn("flex-1 space-y-1.5", hidden && "opacity-60")}>
        <button
          type="button"
          onClick={onLabelClick}
          disabled={!onLabelClick}
          className={cn(
            "flex items-center gap-1 text-sm font-semibold text-std-primary",
            multilineLabel && "whitespace-normal text-left",
            onLabelClick && "cursor-pointer hover:opacity-80",
            !onLabelClick && "cursor-default",
          )}
        >
          {label}
          <ChevronRight className="h-4 w-4 text-std-primary" />
        </button>
        <div className="rounded-xl bg-white px-4 py-3">{children}</div>
      </div>
    </div>
  );
}
