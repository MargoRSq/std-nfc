import {
  AlertDialog,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog";
import { Button } from "@/components/ui/button";

interface Props {
  open: boolean;
  onProceed: () => void;
  onCancel: () => void;
}

export function QuitConfirmModal({ open, onProceed, onCancel }: Props) {
  return (
    <AlertDialog open={open} onOpenChange={(o) => !o && onCancel()}>
      <AlertDialogContent>
        <AlertDialogHeader>
          <AlertDialogTitle>Выйти без сохранения?</AlertDialogTitle>
          <AlertDialogDescription>
            У вас есть несохранённые изменения. Если вы покинете страницу, они будут утеряны.
          </AlertDialogDescription>
        </AlertDialogHeader>
        <AlertDialogFooter>
          <AlertDialogCancel onClick={onCancel}>Остаться</AlertDialogCancel>
          <Button
            type="button"
            className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
            onClick={onProceed}
          >
            Выйти без сохранения
          </Button>
        </AlertDialogFooter>
      </AlertDialogContent>
    </AlertDialog>
  );
}
