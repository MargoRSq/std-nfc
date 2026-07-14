import { useCallback, useEffect, useMemo, useState } from "react";
import * as DialogPrimitive from "@radix-ui/react-dialog";
import Cropper, { type Area } from "react-easy-crop";
import { ArrowLeft, Check } from "lucide-react";
import { toast } from "sonner";
import { cn } from "@/lib/utils";

interface Props {
  src: string | File | null;
  cropShape: "square" | "circle";
  onConfirm: (blob: Blob) => void;
  onCancel: () => void;
}

const MAX_OUT = 1024;

async function cropToBlob(
  imageSrc: string,
  area: Area,
): Promise<Blob> {
  const img = await loadImage(imageSrc);
  const outSize = Math.min(MAX_OUT, Math.round(area.width));
  const canvas = document.createElement("canvas");
  canvas.width = outSize;
  canvas.height = outSize;
  const ctx = canvas.getContext("2d");
  if (!ctx) throw new Error("canvas 2d context unavailable");
  ctx.drawImage(
    img,
    area.x,
    area.y,
    area.width,
    area.height,
    0,
    0,
    outSize,
    outSize,
  );
  return await new Promise<Blob>((resolve, reject) => {
    canvas.toBlob(
      (b) => (b ? resolve(b) : reject(new Error("toBlob failed"))),
      "image/jpeg",
      0.9,
    );
  });
}

function loadImage(src: string): Promise<HTMLImageElement> {
  return new Promise((resolve, reject) => {
    const img = new Image();
    img.crossOrigin = "anonymous";
    img.onload = () => resolve(img);
    img.onerror = (e) => reject(e);
    img.src = src;
  });
}

export default function AvatarCropDialog({ src, cropShape, onConfirm, onCancel }: Props) {
  const [crop, setCrop] = useState({ x: 0, y: 0 });
  const [zoom, setZoom] = useState(1);
  const [area, setArea] = useState<Area | null>(null);
  const [busy, setBusy] = useState(false);

  const objectUrl = useMemo(() => {
    if (!src) return null;
    if (typeof src === "string") return src;
    return URL.createObjectURL(src);
  }, [src]);

  useEffect(() => {
    return () => {
      if (typeof src !== "string" && objectUrl) {
        URL.revokeObjectURL(objectUrl);
      }
    };
  }, [src, objectUrl]);

  const handleCropComplete = useCallback((_: Area, areaPixels: Area) => {
    setArea(areaPixels);
  }, []);

  async function handleConfirm() {
    if (!objectUrl || !area) return;
    setBusy(true);
    try {
      const blob = await cropToBlob(objectUrl, area);
      onConfirm(blob);
    } catch {
      toast.error("Не удалось обрезать изображение");
      setBusy(false);
    }
  }

  return (
    <DialogPrimitive.Root open={src !== null} onOpenChange={(o) => { if (!o) onCancel(); }}>
      <DialogPrimitive.Portal>
        <DialogPrimitive.Overlay className="fixed inset-0 z-50 bg-black/95" />
        <DialogPrimitive.Content
          className="fixed inset-0 z-50 flex flex-col bg-black text-white"
          aria-describedby={undefined}
        >
          <DialogPrimitive.Title className="sr-only">Кадрирование фото</DialogPrimitive.Title>

          <div className="flex items-center justify-between p-4">
            <button
              type="button"
              onClick={onCancel}
              aria-label="Отмена"
              className="flex h-10 w-10 items-center justify-center rounded-full bg-white/10 hover:bg-white/20"
            >
              <ArrowLeft className="h-5 w-5" />
            </button>
            <button
              type="button"
              onClick={handleConfirm}
              disabled={busy || !area}
              aria-label="Подтвердить"
              className={cn(
                "flex h-10 w-10 items-center justify-center rounded-full bg-white text-black hover:bg-white/90 disabled:opacity-50",
              )}
            >
              <Check className="h-5 w-5" />
            </button>
          </div>

          <div className="relative flex-1">
            {objectUrl && (
              <Cropper
                image={objectUrl}
                crop={crop}
                zoom={zoom}
                aspect={1}
                cropShape={cropShape === "circle" ? "round" : "rect"}
                showGrid={false}
                onCropChange={setCrop}
                onZoomChange={setZoom}
                onCropComplete={handleCropComplete}
                style={{
                  containerStyle: { background: "#000" },
                }}
              />
            )}
          </div>

          <div className="flex items-center gap-3 px-6 py-4">
            <input
              type="range"
              min={1}
              max={3}
              step={0.01}
              value={zoom}
              onChange={(e) => setZoom(Number(e.target.value))}
              aria-label="Масштаб"
              className="w-full accent-white"
            />
          </div>
        </DialogPrimitive.Content>
      </DialogPrimitive.Portal>
    </DialogPrimitive.Root>
  );
}
