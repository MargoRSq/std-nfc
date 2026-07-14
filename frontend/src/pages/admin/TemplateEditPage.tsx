import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { ArrowLeft, Check, Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { BackgroundPicker } from "@/components/cards/BackgroundPicker";
import { AvatarColorPicker } from "@/components/cards/AvatarColorPicker";
import { LogoSelector } from "@/components/cards/LogoSelector";
import { ContactBlocksEditor, type ContactBlock } from "@/components/cards/ContactBlocksEditor";
import { CustomFieldsEditor, type CustomField } from "@/components/cards/CustomFieldsEditor";
import { MemberCardPreview } from "@/components/cards/MemberCardPreview";
import { RegionAutocomplete } from "@/components/cards/RegionAutocomplete";
import { templatesApi, type Template } from "@/lib/api/templates";

type PhotoShape = "square" | "circle";
type LogoShape = "square" | "circle" | "rectangle";

interface TemplateStyles {
  bg_kind: "solid" | "gradient";
  bg_color?: string;
  bg_gradient?: { from: string; to: string; angle: number };
  photo_shape: PhotoShape;
  logo_key?: string | null;
  logo_shape?: LogoShape;
  avatar_color?: string;
  avatar_gradient?: { from: string; to: string; angle: number };
}

function extractStyles(t: Template | undefined): TemplateStyles {
  const s = (t?.default_styles ?? {}) as Record<string, unknown>;
  const grad = s.bg_gradient as { from?: string; to?: string; angle?: number } | undefined;
  const avGrad = s.avatar_gradient as { from?: string; to?: string; angle?: number } | undefined;
  return {
    bg_kind: (s.bg_kind as "solid" | "gradient") || "solid",
    bg_color: (s.bg_color as string) || "#1F1E5E",
    bg_gradient: grad && grad.from && grad.to
      ? { from: grad.from, to: grad.to, angle: grad.angle ?? 135 }
      : { from: "#1F1E5E", to: "#798BFF", angle: 135 },
    photo_shape: (s.photo_shape as PhotoShape) || "square",
    logo_key: (s.logo_key as string) || null,
    logo_shape: (s.logo_shape as LogoShape) || "square",
    avatar_color: (s.avatar_color as string) || undefined,
    avatar_gradient: avGrad && avGrad.from && avGrad.to
      ? { from: avGrad.from, to: avGrad.to, angle: avGrad.angle ?? 135 }
      : undefined,
  };
}

function extractFields(t: Template | undefined): {
  chairman: string;
  region: string;
  contacts: ContactBlock[];
} {
  const f = (t?.default_fields ?? {}) as Record<string, unknown>;
  const rawContacts = Array.isArray(f.contacts) ? (f.contacts as ContactBlock[]) : [];
  return {
    chairman: (f.chairman as string) || "",
    region: (f.region as string) || "",
    contacts: rawContacts,
  };
}

function extractSchema(t: Template | undefined): CustomField[] {
  const arr = Array.isArray(t?.custom_field_schema)
    ? (t?.custom_field_schema as unknown as CustomField[])
    : [];
  return arr;
}

export function TemplateEditPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const qc = useQueryClient();

  const { data: template, isLoading } = useQuery({
    queryKey: ["template", id],
    queryFn: () => templatesApi.get(id!).then((r) => r.data),
    enabled: !!id,
  });

  const [name, setName] = useState("");
  const [styles, setStyles] = useState<TemplateStyles>({
    bg_kind: "solid",
    bg_color: "#1F1E5E",
    photo_shape: "square",
    logo_shape: "square",
  });
  const [chairman, setChairman] = useState("");
  const [region, setRegion] = useState("");
  const [contacts, setContacts] = useState<ContactBlock[]>([]);
  const [internalBlocks, setInternalBlocks] = useState<ContactBlock[]>([]);
  const [labelSet, setLabelSet] = useState<CustomField[]>([]);

  useEffect(() => {
    if (template) {
      setName(template.name);
      setStyles(extractStyles(template));
      const f = extractFields(template);
      setChairman(f.chairman);
      setRegion(f.region);
      setContacts(f.contacts.filter((c) => !c.is_internal));
      setInternalBlocks(f.contacts.filter((c) => c.is_internal));
      setLabelSet(extractSchema(template));
    }
  }, [template]);

  const saveMutation = useMutation({
    mutationFn: () => {
      const mergedContacts = [
        ...contacts.map((c) => ({ ...c, is_internal: false })),
        ...internalBlocks.map((c) => ({ ...c, is_internal: true })),
      ];
      return templatesApi.update(id!, {
        name: name.trim(),
        default_styles: {
          bg_kind: styles.bg_kind,
          ...(styles.bg_kind === "solid" ? { bg_color: styles.bg_color } : {}),
          ...(styles.bg_kind === "gradient" ? { bg_gradient: styles.bg_gradient } : {}),
          photo_shape: styles.photo_shape,
          logo_shape: styles.logo_shape,
          ...(styles.logo_key ? { logo_key: styles.logo_key } : {}),
          ...(styles.avatar_color ? { avatar_color: styles.avatar_color } : {}),
          ...(styles.avatar_gradient ? { avatar_gradient: styles.avatar_gradient } : {}),
        },
        default_fields: {
          ...(chairman ? { chairman } : {}),
          ...(region ? { region } : {}),
          ...(mergedContacts.length ? { contacts: mergedContacts } : {}),
        },
        custom_field_schema: labelSet as unknown as Record<string, unknown>[],
      } as Parameters<typeof templatesApi.update>[1] & { custom_field_schema?: unknown });
    },
    onSuccess: () => {
      toast.success("Шаблон сохранён");
      void qc.invalidateQueries({ queryKey: ["templates"] });
      void qc.invalidateQueries({ queryKey: ["template", id] });
      navigate("/admin/templates");
    },
    onError: () => toast.error("Не удалось сохранить шаблон"),
  });

  if (isLoading || !template) {
    return (
      <div className="flex h-[50vh] items-center justify-center">
        <Loader2 className="h-6 w-6 animate-spin text-std-muted-fg" />
      </div>
    );
  }

  const canSave = name.trim().length > 0 && !saveMutation.isPending;

  return (
    <div className="flex flex-col gap-6 px-1 py-4">
      <div className="flex items-center justify-between gap-4">
        <div className="flex items-center gap-3">
          <Button
            variant="ghost"
            size="icon"
            className="h-10 w-10 rounded-full border border-std-border bg-white"
            onClick={() => navigate("/admin/templates")}
            aria-label="Назад"
          >
            <ArrowLeft className="h-4 w-4" />
          </Button>
          <h1 className="text-2xl font-bold">Редактировать шаблон</h1>
        </div>
        <Button
          className="rounded-full bg-std-primary text-white hover:bg-std-primary/90 gap-2"
          onClick={() => saveMutation.mutate()}
          disabled={!canSave}
        >
          {saveMutation.isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : <Check className="h-4 w-4" />}
          Сохранить
        </Button>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-[1fr_360px] gap-6">
        <div className="flex flex-col gap-5">
          <section className="rounded-card border border-std-border bg-white p-5">
            <h2 className="text-lg font-semibold mb-3">Название шаблона</h2>
            <Input
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="Например, Платиновые"
              maxLength={200}
            />
          </section>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
            <section className="rounded-card border border-std-border bg-white p-5">
              <h2 className="text-lg font-semibold mb-3">Аватар</h2>
              <AvatarColorPicker
                value={{
                  bg_kind: styles.avatar_gradient ? "gradient" : "solid",
                  bg_color: styles.avatar_color || "#D6D6D6",
                  bg_gradient: styles.avatar_gradient || { from: "#D6D6D6", to: "#FFFFFF", angle: 135 },
                }}
                onChange={(next) =>
                  setStyles((s) => ({
                    ...s,
                    ...(next.bg_kind === "gradient"
                      ? { avatar_gradient: next.bg_gradient, avatar_color: undefined }
                      : { avatar_color: next.bg_color, avatar_gradient: undefined }),
                  }))
                }
              />
            </section>

            <section className="rounded-card border border-std-border bg-white p-5">
              <h2 className="text-lg font-semibold mb-3">Форма аватара</h2>
              <Tabs
                value={styles.photo_shape}
                onValueChange={(v) => setStyles((s) => ({ ...s, photo_shape: v as PhotoShape }))}
              >
                <TabsList>
                  <TabsTrigger value="square">Квадрат</TabsTrigger>
                  <TabsTrigger value="circle">Круг</TabsTrigger>
                </TabsList>
              </Tabs>
            </section>
          </div>

          <section className="rounded-card border border-std-border bg-white p-5">
            <h2 className="text-lg font-semibold mb-3">Цвет фона карточки</h2>
            <BackgroundPicker
              value={{
                bg_kind: styles.bg_kind,
                bg_color: styles.bg_color,
                bg_gradient: styles.bg_gradient,
              }}
              onChange={(next) =>
                setStyles((s) => ({
                  ...s,
                  bg_kind: next.bg_kind,
                  bg_color: next.bg_color,
                  bg_gradient: next.bg_gradient,
                }))
              }
            />
          </section>

          <section className="rounded-card border border-std-border bg-white p-5">
            <h2 className="text-lg font-semibold mb-3">Логотип</h2>
            <LogoSelector
              value={styles.logo_key ?? null}
              onChange={(v) => setStyles((s) => ({ ...s, logo_key: v }))}
              shape={styles.logo_shape ?? "square"}
              onShapeChange={(shape) => setStyles((s) => ({ ...s, logo_shape: shape }))}
            />
          </section>

          <section className="rounded-card border border-std-border bg-white p-5">
            <h2 className="text-lg font-semibold mb-3">Значения по умолчанию</h2>
            <div className="flex flex-col gap-4">
              <div>
                <label className="text-sm font-medium text-std-muted-fg mb-1.5 block">
                  Председатель союза театральных деятелей
                </label>
                <Input
                  value={chairman}
                  onChange={(e) => setChairman(e.target.value)}
                  placeholder="Иванов И.И."
                />
              </div>
              <div>
                <label className="text-sm font-medium text-std-muted-fg mb-1.5 block">
                  Регион по умолчанию
                </label>
                <RegionAutocomplete value={region} onChange={setRegion} />
              </div>
            </div>
          </section>

          <section className="rounded-card border border-std-border bg-white p-5">
            <h2 className="text-lg font-semibold mb-3">Форма обратной связи с СТД</h2>
            <ContactBlocksEditor value={contacts} onChange={setContacts} addButtonLabel="Добавить контакт" />
          </section>

          <section className="rounded-card border border-std-border bg-[#F5F4FF] border-[3px] border-std-primary/40 p-5">
            <h2 className="text-lg font-semibold mb-3">Служебная информация</h2>
            <ContactBlocksEditor
              value={internalBlocks}
              onChange={setInternalBlocks}
              forceInternal
              addButtonLabel="Добавить поле"
            />
          </section>

          <section className="rounded-card border border-std-border bg-white p-5">
            <h2 className="text-lg font-semibold mb-3">Дополнительные поля</h2>
            <CustomFieldsEditor value={labelSet} onChange={setLabelSet} />
          </section>
        </div>

        <div className="flex flex-col gap-3">
          <h2 className="text-lg font-semibold">Предпросмотр</h2>
          <MemberCardPreview
            payload={{
              last_name: "Иванов",
              first_name: "Иван",
              middle_name: "Иванович",
              membership_no: "XXXX",
              category_id: template.category_id ?? 1,
              photo_shape: styles.photo_shape,
              bg_kind: styles.bg_kind,
              bg_color: styles.bg_color,
              bg_gradient: styles.bg_gradient,
              avatar_color: styles.avatar_color ?? null,
              avatar_gradient: styles.avatar_gradient ?? null,
              label_set: labelSet,
              field_order: ["birth_date", "region", "card_issue_date", "join_date", "chairman"],
              contacts: [
                ...contacts.map((c) => ({ ...c, is_internal: false })),
                ...internalBlocks.map((c) => ({ ...c, is_internal: true })),
              ],
              internal_blocks: [],
              region: region || undefined,
              chairman: chairman || undefined,
              hide_birth_date: true,
              hide_region: !region,
              hide_card_issue_date: true,
              hide_join_date: true,
              hide_chairman: !chairman,
              feedback_form_enabled: true,
              logo_key: styles.logo_key ?? null,
              logo_shape: styles.logo_shape ?? "square",
              photo_key: null,
            }}
          />
        </div>
      </div>
    </div>
  );
}
