import { useEffect, useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useNavigate } from "react-router-dom";
import { toast } from "sonner";
import { ArrowLeft, Trash2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import { ContactBlocksEditor, type ContactBlock } from "@/components/cards/ContactBlocksEditor";
import { DEFAULT_REGION, regionContactsApi } from "@/lib/api/regionContacts";
import { REGIONS } from "@/lib/data/regions";
import { useAuthStore } from "@/stores/authStore";

const DEFAULT_LABEL = "Все остальные регионы";

function regionLabel(region: string) {
  return region === DEFAULT_REGION ? DEFAULT_LABEL : region;
}

export function RegionContactsPage() {
  const qc = useQueryClient();
  const navigate = useNavigate();
  const canEdit = useAuthStore((s) => s.user?.role) !== "viewer";
  const [region, setRegion] = useState<string>(DEFAULT_REGION);
  const [contacts, setContacts] = useState<ContactBlock[]>([]);

  const { data: rows, isLoading } = useQuery({
    queryKey: ["region-contacts"],
    queryFn: () => regionContactsApi.list().then((r) => r.data),
  });

  const current = useMemo(() => rows?.find((r) => r.region === region), [rows, region]);

  useEffect(() => {
    setContacts(current?.contacts ?? []);
  }, [current, region]);

  const saveMutation = useMutation({
    mutationFn: () => regionContactsApi.upsert(region, contacts).then((r) => r.data),
    onSuccess: () => {
      toast.success(`Контакты сохранены: ${regionLabel(region)}`);
      qc.invalidateQueries({ queryKey: ["region-contacts"] });
    },
    onError: () => toast.error("Не удалось сохранить контакты"),
  });

  const deleteMutation = useMutation({
    mutationFn: () => regionContactsApi.remove(region),
    onSuccess: () => {
      toast.success("Контакты региона удалены");
      qc.invalidateQueries({ queryKey: ["region-contacts"] });
      setRegion(DEFAULT_REGION);
    },
    onError: () => toast.error("Не удалось удалить контакты"),
  });

  const configured = rows?.map((r) => r.region) ?? [];
  const options = [DEFAULT_REGION, ...REGIONS.filter((r) => r !== DEFAULT_REGION)];

  return (
    <div className="space-y-4 max-w-[900px] mx-auto">
      <div className="flex items-center gap-4">
        <button
          type="button"
          onClick={() => navigate("/admin/cards")}
          className="h-8 w-8 rounded-full border border-std-border bg-white flex items-center justify-center hover:bg-std-surface-2 transition-colors shrink-0"
          aria-label="Назад к карточкам"
        >
          <ArrowLeft className="h-4 w-4 text-std-muted-fg" />
        </button>
        <h1 className="text-xl font-semibold">Контакты по регионам</h1>
      </div>

      <p className="text-sm text-std-muted">
        Эти контакты показываются в окне «Связаться с нами» на публичной карточке, если у самой
        карточки контакты не заполнены. Регион берётся из карточки; если для него записи нет,
        показываются контакты «{DEFAULT_LABEL}».
      </p>

      <section className="rounded-3xl border border-std-border bg-white px-4 py-3 space-y-3">
        <div className="flex items-center gap-3">
          <Select value={region} onValueChange={setRegion}>
            <SelectTrigger className="w-[320px] rounded-xl">
              <SelectValue placeholder="Выберите регион" />
            </SelectTrigger>
            <SelectContent>
              {options.map((r) => (
                <SelectItem key={r} value={r}>
                  {regionLabel(r)}
                  {configured.includes(r) ? " ✓" : ""}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
          <div className="flex-1" />
          {canEdit && current && region !== DEFAULT_REGION && (
            <Button
              type="button"
              variant="ghost"
              onClick={() => deleteMutation.mutate()}
              disabled={deleteMutation.isPending}
            >
              <Trash2 className="size-4" />
              Удалить
            </Button>
          )}
          {canEdit && (
            <Button
              type="button"
              onClick={() => saveMutation.mutate()}
              disabled={saveMutation.isPending}
            >
              {saveMutation.isPending ? "Сохраняем…" : "Сохранить"}
            </Button>
          )}
        </div>

        {isLoading ? (
          <Skeleton className="h-24 w-full" />
        ) : (
          <ContactBlocksEditor
            value={contacts}
            onChange={setContacts}
            addButtonLabel="Добавить контакт"
          />
        )}
      </section>

      {configured.length > 0 && (
        <section className="rounded-3xl border border-std-border bg-white px-4 py-3">
          <h2 className="text-base font-semibold text-std-ink mb-2">Заполненные регионы</h2>
          <div className="flex flex-wrap gap-2">
            {configured.map((r) => (
              <button
                key={r}
                type="button"
                onClick={() => setRegion(r)}
                className="rounded-pill border border-std-border px-3 py-1 text-sm hover:bg-std-surface-2"
              >
                {regionLabel(r)}
              </button>
            ))}
          </div>
        </section>
      )}
    </div>
  );
}
