import { useNavigate } from "react-router-dom";
import { CheckCircle2 } from "lucide-react";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";

interface Props {
  open: boolean;
  title: string;
  description?: string;
  homeHref?: string;
  onClose: () => void;
}

export function SaveSuccessModal({
  open,
  title,
  description,
  homeHref = "/admin/cards",
  onClose,
}: Props) {
  const navigate = useNavigate();

  function handleHome() {
    onClose();
    navigate(homeHref);
  }

  return (
    <Dialog open={open} onOpenChange={(o) => !o && onClose()}>
      <DialogContent className="max-w-sm text-center">
        <DialogHeader className="items-center">
          <CheckCircle2 className="h-12 w-12 text-emerald-500" />
          <DialogTitle>{title}</DialogTitle>
          {description && <DialogDescription>{description}</DialogDescription>}
        </DialogHeader>
        <Button onClick={handleHome} className="w-full">
          Вернуться на главную
        </Button>
      </DialogContent>
    </Dialog>
  );
}
