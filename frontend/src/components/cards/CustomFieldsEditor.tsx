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
  verticalListSortingStrategy,
} from "@dnd-kit/sortable";
import { Plus } from "lucide-react";
import {
  SortableCustomFieldRow,
  genFieldKey,
  type CustomField,
} from "./CustomFieldRow";

export type { CustomField } from "./CustomFieldRow";

interface Props {
  value: CustomField[];
  onChange: (next: CustomField[]) => void;
  onLabelClick?: (idx: number) => void;
}

export function CustomFieldsEditor({ value, onChange, onLabelClick }: Props) {
  const [ids, setIds] = useState<string[]>(() => value.map(() => genFieldKey()));
  const prevLenRef = useRef(value.length);

  useEffect(() => {
    const prev = prevLenRef.current;
    prevLenRef.current = value.length;
    if (value.length > ids.length) {
      setIds((cur) => {
        const next = [...cur];
        for (let i = cur.length; i < value.length; i++) next.push(genFieldKey());
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

  function addField() {
    const newKey = genFieldKey();
    setIds((prev) => [...prev, newKey]);
    onChange([...value, { key: newKey, label: "", value: "", type: "text" }]);
  }

  function updateAt(idx: number, patch: Partial<CustomField>) {
    onChange(value.map((f, i) => (i === idx ? { ...f, ...patch } : f)));
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
    setIds(arrayMove(ids, oldIdx, newIdx));
    onChange(arrayMove(value, oldIdx, newIdx));
  }

  return (
    <div className="space-y-2">
      <DndContext sensors={sensors} collisionDetection={closestCenter} onDragEnd={handleDragEnd}>
        <SortableContext items={ids} strategy={verticalListSortingStrategy}>
          {value.map((field, idx) => (
            <SortableCustomFieldRow
              key={ids[idx] ?? idx}
              id={ids[idx] ?? String(idx)}
              field={field}
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
        onClick={addField}
        className="flex h-12 w-full items-center justify-start gap-2 rounded-xl border border-std-border bg-white px-5 text-sm font-semibold text-std-primary transition-colors hover:bg-std-surface-2"
      >
        <Plus className="h-5 w-5" />
        Добавить поле
      </button>
    </div>
  );
}
