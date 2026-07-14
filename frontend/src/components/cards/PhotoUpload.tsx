import { lazy, Suspense, useRef, useState } from "react";
import { Upload } from "lucide-react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { apiClient } from "@/lib/api/client";

const AvatarCropDialog = lazy(() => import("./AvatarCropDialog"));

interface Props {
  cardId: string;
  initialKey?: string | null;
  shape?: "square" | "circle";
  onUploaded: (key: string) => void;
  type?: "photo" | "logo";
  cropShape?: "square" | "circle";
}

export function PhotoUpload({
  cardId,
  initialKey,
  shape = "square",
  onUploaded,
  type = "photo",
  cropShape,
}: Props) {
  const [uploading, setUploading] = useState(false);
  const [key, setKey] = useState<string | null>(initialKey ?? null);
  const [pendingFile, setPendingFile] = useState<File | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  async function uploadBlob(payload: Blob, filename: string) {
    setUploading(true);
    try {
      const form = new FormData();
      form.append("file", payload, filename);
      const path = type === "photo" ? `/cards/${cardId}/photo` : `/cards/${cardId}/logo`;
      const r = await apiClient.post(path, form, {
        headers: { "Content-Type": "multipart/form-data" },
      });
      const newKey = r.data[type === "photo" ? "photo_key" : "logo_key"] as string;
      setKey(newKey);
      onUploaded(newKey);
      toast.success("Загружено");
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

  async function handleFile(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file) return;
    if (file.size > 5 * 1024 * 1024) {
      toast.error("Изображение больше 5 МБ");
      if (inputRef.current) inputRef.current.value = "";
      return;
    }
    if (!/^image\/(jpeg|png|webp)$/.test(file.type)) {
      toast.error("Поддерживаются только JPEG, PNG, WEBP");
      if (inputRef.current) inputRef.current.value = "";
      return;
    }
    if (cropShape) {
      setPendingFile(file);
      return;
    }
    await uploadBlob(file, file.name);
  }

  function handleCropConfirm(blob: Blob) {
    setPendingFile(null);
    void uploadBlob(blob, "avatar.jpg");
  }

  function handleCropCancel() {
    setPendingFile(null);
    if (inputRef.current) inputRef.current.value = "";
  }

  return (
    <div className="flex flex-col items-center gap-3">
      <div
        className={`bg-muted relative flex h-32 w-32 cursor-pointer items-center justify-center overflow-hidden border-2 border-dashed ${shape === "circle" ? "rounded-full" : "rounded-lg"}`}
        onClick={() => inputRef.current?.click()}
      >
        {key ? (
          <img src={`/api/media/${key}`} alt="" className="h-full w-full object-cover" />
        ) : (
          <Upload className="text-muted-foreground h-8 w-8" />
        )}
      </div>
      <input
        ref={inputRef}
        type="file"
        accept="image/jpeg,image/png,image/webp"
        onChange={handleFile}
        className="hidden"
        data-photo-input="true"
      />
      <Button
        variant="outline"
        size="sm"
        disabled={uploading}
        onClick={() => inputRef.current?.click()}
        type="button"
      >
        {uploading ? "Загрузка…" : key ? "Заменить" : "Загрузить"}
      </Button>

      {pendingFile && cropShape && (
        <Suspense fallback={null}>
          <AvatarCropDialog
            src={pendingFile}
            cropShape={cropShape}
            onConfirm={handleCropConfirm}
            onCancel={handleCropCancel}
          />
        </Suspense>
      )}
    </div>
  );
}
