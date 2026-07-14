import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog";

export interface DiffEntry {
  label: string;
  before: string;
  after: string;
}

interface Props {
  open: boolean;
  diffs: DiffEntry[];
  onConfirm: () => void;
  onCancel: () => void;
  isPending?: boolean;
}

export function ApproveSaveModal({ open, diffs, onConfirm, onCancel, isPending }: Props) {
  return (
    <AlertDialog open={open} onOpenChange={(o) => !o && onCancel()}>
      <AlertDialogContent>
        <AlertDialogHeader>
          <AlertDialogTitle>Подтвердите изменения</AlertDialogTitle>
          <AlertDialogDescription>
            Эти ключевые поля будут изменены. Проверьте перед сохранением.
          </AlertDialogDescription>
        </AlertDialogHeader>
        <ul className="space-y-2 text-sm max-h-60 overflow-y-auto">
          {diffs.map((d) => (
            <li key={d.label} className="rounded-lg border border-std-border p-3">
              <p className="font-medium text-std-ink-strong">{d.label}</p>
              <p className="text-std-muted-fg">
                <span className="line-through">{d.before || "—"}</span>
                {" → "}
                <span className="font-semibold text-std-primary">{d.after || "—"}</span>
              </p>
            </li>
          ))}
        </ul>
        <AlertDialogFooter>
          <AlertDialogCancel onClick={onCancel}>Отмена</AlertDialogCancel>
          <AlertDialogAction onClick={onConfirm} disabled={isPending}>
            {isPending ? "Сохранение…" : "Сохранить"}
          </AlertDialogAction>
        </AlertDialogFooter>
      </AlertDialogContent>
    </AlertDialog>
  );
}
