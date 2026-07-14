import { useEffect, useRef, useState } from "react";
import { Trash2, Plus } from "lucide-react";
import { toast } from "sonner";
import { apiClient } from "@/lib/api/client";
import { cn } from "@/lib/utils";
import {
  isPresetKey,
  presetIdFromKey,
  presetUrl,
} from "@/lib/logoPresets";

export type LogoShape = "square" | "circle" | "rectangle";

interface Props {
  value: string | null;
  cardId?: string;
  onChange: (value: string | null) => void;
  shape?: LogoShape;
  onShapeChange?: (shape: LogoShape) => void;
  pendingFile?: File | null;
  onPendingFileChange?: (file: File | null) => void;
}

export function LogoSelector({
  value,
  cardId,
  onChange,
  shape = "square",
  onShapeChange,
  pendingFile,
  onPendingFileChange,
}: Props) {
  const [uploading, setUploading] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);
  const [pendingPreviewUrl, setPendingPreviewUrl] = useState<string | null>(null);

  useEffect(() => {
    if (!pendingFile) {
      setPendingPreviewUrl(null);
      return;
    }
    const url = URL.createObjectURL(pendingFile);
    setPendingPreviewUrl(url);
    return () => URL.revokeObjectURL(url);
  }, [pendingFile]);

  const isPreset = isPresetKey(value);
  const selectedPresetId = isPreset ? presetIdFromKey(value as string) : null;
  const isUploaded = !isPreset && !!value;
  const uploadedUrl = isUploaded ? `/api/media/${value}` : null;

  const canUpload = !!cardId || !!onPendingFileChange;

  async function handleFile(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file) return;
    if (!cardId) {
      onPendingFileChange?.(file);
      if (inputRef.current) inputRef.current.value = "";
      return;
    }
    setUploading(true);
    try {
      const form = new FormData();
      form.append("file", file);
      const r = await apiClient.post(`/cards/${cardId}/logo`, form, {
        headers: { "Content-Type": "multipart/form-data" },
      });
      const newKey = r.data.logo_key as string;
      onChange(newKey);
      toast.success("Логотип загружен");
    } catch (err: unknown) {
      const message =
        err && typeof err === "object" && "response" in err
          ? (err as { response?: { data?: { message?: string } } }).response?.data?.message
          : undefined;
      toast.error(message || "Ошибка загрузки");
    } finally {
      setUploading(false);
      if (inputRef.current) inputRef.current.value = "";
    }
  }

  const logoImgUrl =
    pendingPreviewUrl ?? uploadedUrl ?? (selectedPresetId ? presetUrl(selectedPresetId) : null);

  const hasLogo = !!pendingFile || value !== null;

  const shapeButtons: { value: LogoShape; innerCss: React.CSSProperties; label: string }[] = [
    { value: "square",    innerCss: { width: 60, height: 60, borderRadius: 10 },       label: "Квадратная форма логотипа" },
    { value: "circle",    innerCss: { width: 60, height: 60, borderRadius: "50%" },    label: "Круглая форма логотипа" },
    { value: "rectangle", innerCss: { width: 100, height: 56, borderRadius: 10 },      label: "Прямоугольная форма логотипа" },
  ];

  return (
    <div className="flex flex-col gap-3">
      <button
        type="button"
        disabled={!canUpload || uploading}
        onClick={() => inputRef.current?.click()}
        className="flex h-12 w-full items-center gap-2 rounded-xl border border-std-border bg-white px-4 text-sm font-semibold text-std-primary transition-colors hover:bg-std-surface-2 disabled:opacity-50"
      >
        <Plus className="h-5 w-5" />
        {uploading ? "Загрузка…" : "Загрузить логотип"}
      </button>

      <input
        ref={inputRef}
        type="file"
        accept="image/jpeg,image/png,image/webp"
        onChange={handleFile}
        className="hidden"
        data-logo-input="true"
      />

      <div className="flex items-center gap-2.5">
        {shapeButtons.map((opt) => {
          const isShapeActive = shape === opt.value;
          const showLogo = !!logoImgUrl;
          return (
            <button
              key={opt.value}
              type="button"
              onClick={() => {
                if (onShapeChange) onShapeChange(opt.value);
              }}
              aria-label={opt.label}
              aria-pressed={isShapeActive}
              className={cn(
                "flex h-20 items-center justify-center bg-white transition-colors",
                opt.value === "rectangle" ? "w-[120px] rounded-2xl" : "w-20",
                opt.value === "circle" && "rounded-full",
                opt.value === "square" && "rounded-2xl",
                isShapeActive
                  ? "border-2 border-std-primary"
                  : "border border-std-border hover:border-foreground/40",
              )}
            >
              {showLogo && (
                <div
                  style={{ ...opt.innerCss, overflow: "hidden", background: "#FFFFFF" }}
                  className="flex items-center justify-center"
                >
                  <img src={logoImgUrl!} alt="" className="h-full w-full object-contain" />
                </div>
              )}
            </button>
          );
        })}
      </div>

      <button
        type="button"
        disabled={!hasLogo}
        onClick={() => {
          if (pendingFile) {
            onPendingFileChange?.(null);
          }
          onChange(null);
        }}
        className="flex h-12 w-full items-center justify-center gap-2 rounded-xl border border-std-border bg-white text-sm font-semibold text-std-ink transition-colors hover:bg-std-surface-2 disabled:opacity-50"
      >
        <Trash2 className="h-5 w-5 text-[#DC2626]" />
        Удалить
      </button>
    </div>
  );
}
