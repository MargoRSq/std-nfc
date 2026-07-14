import { useEffect, useState } from "react";
import { Check, Loader2, RefreshCw } from "lucide-react";
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { cardsApi } from "@/lib/api/cards";
import { useDebounce } from "@/hooks/useDebounce";

interface Props {
  open: boolean;
  onClose: () => void;
  onConfirm: (slug: string) => void;
  submitting?: boolean;
}

// Точка разрешена внутри, но не первым/последним символом и не подряд («..»).
const SLUG_PATTERN = /^[A-Za-z0-9_-][A-Za-z0-9_.-]*[A-Za-z0-9_-]$/;
const URL_PREFIX = `${window.location.origin}/c/`;
const SLUG_ALPHABET = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789";

function generateSlug(length = 7): string {
  let out = "";
  const arr = new Uint8Array(length);
  crypto.getRandomValues(arr);
  for (let i = 0; i < length; i++) {
    out += SLUG_ALPHABET[arr[i] % SLUG_ALPHABET.length];
  }
  return out;
}

export function SlugCreateModal({ open, onClose, onConfirm, submitting }: Props) {
  const [value, setValue] = useState("");
  const [available, setAvailable] = useState<boolean | null>(null);
  const [checking, setChecking] = useState(false);
  const debounced = useDebounce(value, 350);

  useEffect(() => {
    if (open) {
      setValue(generateSlug());
      setAvailable(null);
    } else {
      setValue("");
      setAvailable(null);
    }
  }, [open]);

  useEffect(() => {
    if (!open || !debounced) {
      setAvailable(null);
      return;
    }
    if (debounced.length < 3 || debounced.length > 32) {
      setAvailable(false);
      return;
    }
    if (!SLUG_PATTERN.test(debounced)) {
      setAvailable(false);
      return;
    }
    let cancelled = false;
    setChecking(true);
    cardsApi
      .checkSlug(debounced)
      .then((r) => {
        if (!cancelled) setAvailable(r.data.available);
      })
      .catch(() => {
        if (!cancelled) setAvailable(null);
      })
      .finally(() => {
        if (!cancelled) setChecking(false);
      });
    return () => {
      cancelled = true;
    };
  }, [debounced, open]);

  const formatError =
    value.length > 0 && (value.length < 6 || value.length > 32)
      ? "URL должен быть от 6 до 32 символов"
      : value.length > 0 && (!SLUG_PATTERN.test(value) || value.includes(".."))
        ? "Латинские буквы, цифры, _ - и точка. Точка — только внутри, не подряд"
        : null;
  const takenError = available === false && !formatError ? "Данный URL занят, придумайте другой" : null;
  const canSubmit = !!value && available === true && !formatError && !submitting;

  return (
    <Dialog open={open} onOpenChange={(o) => !o && onClose()}>
      <DialogContent className="max-w-md">
        <DialogHeader>
          <DialogTitle className="text-center">Создайте URL удостоверения</DialogTitle>
        </DialogHeader>
        <div className="space-y-3">
          {takenError && (
            <p className="text-sm text-destructive font-medium text-center">{takenError}</p>
          )}
          <div className="flex items-stretch rounded-md border border-input bg-background overflow-hidden">
            <span className="px-3 inline-flex items-center text-xs text-muted-foreground bg-muted whitespace-nowrap">
              {URL_PREFIX}
            </span>
            <Input
              autoFocus
              value={value}
              onChange={(e) => setValue(e.target.value.trim())}
              placeholder="example"
              className="border-0 rounded-none focus-visible:ring-0"
            />
            <button
              type="button"
              onClick={() => setValue(generateSlug())}
              aria-label="Сгенерировать новый"
              className="px-3 inline-flex items-center text-muted-foreground hover:text-foreground border-l border-input"
            >
              <RefreshCw className="h-4 w-4" />
            </button>
          </div>
          <p className="text-xs text-muted-foreground">
            URL предложен автоматически. Можно отредактировать или сгенерировать заново.
          </p>
          {formatError && (
            <p className="text-xs text-destructive">{formatError}</p>
          )}
          <div className="text-xs text-destructive font-semibold">
            БУДЬТЕ ВНИМАТЕЛЬНЫ:
            <span className="font-normal text-destructive/80 block">URL можно создать только один раз</span>
          </div>
          <p className="text-xs text-muted-foreground">
            Введите любое сочетание латинских букв, цифр и знаков.
          </p>
          <Button
            type="button"
            onClick={() => onConfirm(value)}
            disabled={!canSubmit}
            className="w-full rounded-pill bg-std-primary hover:bg-std-primary/90"
          >
            {submitting ? (
              <Loader2 className="h-4 w-4 mr-2 animate-spin" />
            ) : checking ? (
              <Loader2 className="h-4 w-4 mr-2 animate-spin" />
            ) : (
              <Check className="h-4 w-4 mr-2" />
            )}
            Сохранить
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  );
}
