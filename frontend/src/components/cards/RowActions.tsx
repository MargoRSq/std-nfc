import { Trash2, ChevronDown, ChevronUp, Eye, EyeOff } from "lucide-react";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

interface RowActionsProps {
  onDelete?: () => void;
  onToggleCollapse?: () => void;
  onToggleHidden?: () => void;
  collapsed?: boolean;
  hidden?: boolean;
  canDelete?: boolean;
  className?: string;
}

export function RowActions({
  onDelete,
  onToggleCollapse,
  onToggleHidden,
  collapsed,
  hidden,
  canDelete = true,
  className,
}: RowActionsProps) {
  return (
    <div className={cn("flex items-center gap-2 w-full", className)}>
      {canDelete && onDelete && (
        <Button
          type="button"
          variant="outline"
          size="sm"
          onClick={onDelete}
          className="flex-1 h-9 px-3 rounded-lg border-std-border bg-white text-std-ink hover:bg-std-surface-2 text-xs font-normal"
        >
          <Trash2 className="h-3.5 w-3.5 mr-1.5 text-[#DC2626]" />
          Удалить
        </Button>
      )}
      {onToggleCollapse && (
        <Button
          type="button"
          variant="outline"
          size="sm"
          onClick={onToggleCollapse}
          className="flex-1 h-9 px-3 rounded-lg border-std-border bg-white text-std-primary hover:bg-std-primary/5 text-xs font-normal"
          title={collapsed ? "Развернуть поле" : "Свернуть поле"}
        >
          {collapsed ? (
            <ChevronDown className="h-3.5 w-3.5 mr-1.5" />
          ) : (
            <ChevronUp className="h-3.5 w-3.5 mr-1.5" />
          )}
          {collapsed ? "Открыть" : "Свернуть"}
        </Button>
      )}
      {onToggleHidden && (
        <Button
          type="button"
          variant="outline"
          size="sm"
          onClick={onToggleHidden}
          className="flex-1 h-9 px-3 rounded-lg border-std-border bg-white text-std-primary hover:bg-std-primary/5 text-xs font-normal"
          title={
            hidden
              ? "Сейчас скрыто на публичной карточке — вернуть"
              : "Видно на публичной карточке — скрыть"
          }
        >
          {hidden ? (
            <Eye className="h-3.5 w-3.5 mr-1.5" />
          ) : (
            <EyeOff className="h-3.5 w-3.5 mr-1.5" />
          )}
          {hidden ? "Показать" : "Скрыть"}
        </Button>
      )}
    </div>
  );
}
