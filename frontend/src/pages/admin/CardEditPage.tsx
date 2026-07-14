import { lazy, Suspense, useCallback, useEffect, useRef, useState } from "react";
import { useParams, useNavigate, useSearchParams } from "react-router-dom";
import { useForm, useWatch } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { ArrowLeft, Check, ChevronRight, Loader2, X } from "lucide-react";
import {
  DndContext,
  closestCenter,
  KeyboardSensor,
  PointerSensor,
  useSensor,
  useSensors,
  type DragEndEvent,
} from "@dnd-kit/core";
import {
  arrayMove,
  SortableContext,
  sortableKeyboardCoordinates,
  verticalListSortingStrategy,
} from "@dnd-kit/sortable";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { Form, FormControl, FormField, FormItem, FormLabel, FormMessage } from "@/components/ui/form";
import { Input } from "@/components/ui/input";
import { Skeleton } from "@/components/ui/skeleton";
import { FioInput } from "@/components/cards/FioInput";
import { SortablePresetRow } from "@/components/cards/SortablePresetRow";
import { defaultFieldOrder, buildFieldRenderOrder } from "@/components/cards/cardFields";
import { LogoSelector } from "@/components/cards/LogoSelector";
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { defaultLogoKey } from "@/lib/logoPresets";
import { BackgroundPicker } from "@/components/cards/BackgroundPicker";
import { AvatarColorPicker } from "@/components/cards/AvatarColorPicker";
const AvatarCropDialog = lazy(() => import("@/components/cards/AvatarCropDialog"));
import { ContactBlocksEditor, type ContactBlock } from "@/components/cards/ContactBlocksEditor";
import { contactTypeFromPreset } from "@/lib/cards/contactTypeFromPreset";
import { type CustomField } from "@/components/cards/CustomFieldsEditor";
import {
  SortableCustomFieldRow,
  genFieldKey,
} from "@/components/cards/CustomFieldRow";
import { Plus } from "lucide-react";
import { LabelPickerSheet } from "@/components/cards/LabelPickerSheet";
import { MemberCardPreview } from "@/components/cards/MemberCardPreview";
import { RegionAutocomplete } from "@/components/cards/RegionAutocomplete";
import { DatePickerField } from "@/components/cards/DatePickerField";
import { QuitConfirmModal } from "@/components/cards/QuitConfirmModal";
import { ApproveSaveModal, type DiffEntry } from "@/components/cards/ApproveSaveModal";
import { SaveSuccessModal } from "@/components/cards/SaveSuccessModal";
import { SlugCreateModal } from "@/components/cards/SlugCreateModal";
import { useDirtyFormBlocker } from "@/hooks/useDirtyFormBlocker";
import { cardsApi, type CardCreateRequest } from "@/lib/api/cards";
import { cardMessagesApi } from "@/lib/api/cardMessages";
import { templatesApi } from "@/lib/api/templates";
import { apiClient } from "@/lib/api/client";
import axios from "axios";

interface ApiError {
  code?: string;
  message: string;
  details?: { field?: string; [k: string]: unknown };
}

function extractApiError(err: unknown): ApiError | null {
  if (axios.isAxiosError(err)) {
    const data = err.response?.data as { code?: string; message?: string; details?: Record<string, unknown> } | undefined;
    if (data?.message) {
      return { code: data.code, message: data.message, details: data.details as ApiError["details"] };
    }
  }
  return null;
}

function formatValidationErrors(apiErr: ApiError | null): string | null {
  const errs = apiErr?.details?.errors;
  if (!Array.isArray(errs) || errs.length === 0) return null;
  const lines = errs.slice(0, 5).map((e) => {
    const err = e as { loc?: unknown[]; msg?: string };
    const loc = Array.isArray(err.loc) ? err.loc.filter((p) => p !== "body").join(".") : "?";
    return `${loc}: ${err.msg ?? "invalid"}`;
  });
  return lines.join("\n");
}

const cardSchema = z.object({
  last_name: z.string().min(1, "Фамилия обязательна"),
  first_name: z.string().min(1, "Имя обязательно"),
  middle_name: z.string().optional(),
  category_id: z.number().optional(),
  membership_no: z.string().min(1, "Номер билета обязателен"),
  birth_date: z.string().optional(),
  region: z.string().optional(),
  card_issue_date: z.string().optional(),
  join_date: z.string().optional(),
  chairman: z.string().optional(),
  bg_kind: z.enum(["solid", "gradient"]).default("solid"),
  bg_color: z.string().optional(),
  bg_gradient_from: z.string().optional(),
  bg_gradient_to: z.string().optional(),
  bg_gradient_angle: z.number().optional(),
  avatar_color: z.string().optional(),
  avatar_gradient_from: z.string().optional(),
  avatar_gradient_to: z.string().optional(),
  avatar_gradient_angle: z.number().optional(),
  photo_shape: z.enum(["square", "circle"]).default("square"),
  hide_birth_date: z.boolean().default(false),
  hide_region: z.boolean().default(false),
  hide_card_issue_date: z.boolean().default(false),
  hide_join_date: z.boolean().default(false),
  hide_chairman: z.boolean().default(false),
  feedback_form_enabled: z.boolean().default(true),
  template_id: z.string().optional(),
});

type CardFormData = z.infer<typeof cardSchema>;

interface CardEditPageProps {
  mode: "create" | "edit";
}

export function CardEditPage({ mode }: CardEditPageProps) {
  const { id } = useParams<{ id: string }>();
  const [searchParams] = useSearchParams();
  const initialTemplateId = searchParams.get("template_id");
  const navigate = useNavigate();
  const qc = useQueryClient();
  const [, setSlugValue] = useState("");
  const [photoKey, setPhotoKey] = useState<string | null>(null);
  const [logoKey, setLogoKey] = useState<string | null>(
    mode === "create" ? defaultLogoKey() : null,
  );
  const [logoShape, setLogoShape] = useState<"square" | "circle" | "rectangle">(
    mode === "create" ? "rectangle" : "square",
  );
  const [photoShape, setPhotoShape] = useState<"square" | "circle">("square");
  const [fieldOrder, setFieldOrder] = useState<string[]>(() => defaultFieldOrder());
  const dndSensors = useSensors(
    useSensor(PointerSensor),
    useSensor(KeyboardSensor, { coordinateGetter: sortableKeyboardCoordinates }),
  );
  const [contacts, setContacts] = useState<ContactBlock[]>([]);
  const [internalBlocks, setInternalBlocks] = useState<ContactBlock[]>([]);
  const [pendingPhotoFile, setPendingPhotoFile] = useState<File | null>(null);
  const [pendingPhotoPreview, setPendingPhotoPreview] = useState<string | null>(null);
  const [pendingCropSrc, setPendingCropSrc] = useState<File | string | null>(null);
  const [pendingLogoFile, setPendingLogoFile] = useState<File | null>(null);
  const [pendingLogoPreview, setPendingLogoPreview] = useState<string | null>(null);
  const [labelSet, setLabelSet] = useState<CustomField[]>([]);
  const [fieldLabels, setFieldLabels] = useState<Record<string, string>>({});
  const [pickerTarget, setPickerTarget] = useState<
    | { kind: "field"; key: string }
    | { kind: "contact"; idx: number }
    | { kind: "internal"; idx: number }
    | { kind: "custom"; key: string }
    | null
  >(null);

  const handleFieldOrderDragEnd = (event: DragEndEvent) => {
    const { active, over } = event;
    if (!over || active.id === over.id) return;
    setFieldOrder((prev) => {
      const order = buildFieldRenderOrder(prev, labelSet)
        .filter((it) => !(it.kind === "preset" && it.key === "chairman"))
        .map((it) => (it.kind === "preset" ? it.key : it.field.key));
      const oldIdx = order.indexOf(String(active.id));
      const newIdx = order.indexOf(String(over.id));
      if (oldIdx < 0 || newIdx < 0) return prev;
      return [...arrayMove(order, oldIdx, newIdx), "chairman"];
    });
    setUserInteracted(true);
  };

  const addCustomField = () => {
    const key = genFieldKey();
    setLabelSet((prev) => [...prev, { key, label: "", value: "", type: "text" }]);
    setFieldOrder((prev) => {
      const withoutChair = prev.filter((k) => k !== "chairman");
      return [...withoutChair, key, "chairman"];
    });
    setUserInteracted(true);
  };

  const updateCustomField = (key: string, patch: Partial<CustomField>) => {
    setLabelSet((prev) => prev.map((f) => (f.key === key ? { ...f, ...patch } : f)));
    setUserInteracted(true);
  };

  const removeCustomField = (key: string) => {
    setLabelSet((prev) => prev.filter((f) => f.key !== key));
    setFieldOrder((prev) => prev.filter((k) => k !== key));
    setUserInteracted(true);
  };

  const editorFields = buildFieldRenderOrder(fieldOrder, labelSet).filter(
    (it) => !(it.kind === "preset" && it.key === "chairman"),
  );
  const editorIds = editorFields.map((it) =>
    it.kind === "preset" ? it.key : it.field.key,
  );

  const openPicker = useCallback(
    (target: Exclude<typeof pickerTarget, null>) => setPickerTarget(target),
    [],
  );

  const applyPickedLabel = useCallback(
    (name: string, type: CustomField["type"]) => {
      if (!pickerTarget) return;
      if (pickerTarget.kind === "field") {
        setFieldLabels((prev) => ({ ...prev, [pickerTarget.key]: name }));
        setUserInteracted(true);
      } else if (pickerTarget.kind === "contact") {
        const ct = contactTypeFromPreset(name, type);
        setContacts((prev) =>
          prev.map((c, i) =>
            i === pickerTarget.idx
              ? { ...c, label: name, input_type: type, type: ct ?? c.type }
              : c,
          ),
        );
        setUserInteracted(true);
      } else if (pickerTarget.kind === "internal") {
        const ct = contactTypeFromPreset(name, type);
        setInternalBlocks((prev) =>
          prev.map((c, i) =>
            i === pickerTarget.idx
              ? { ...c, label: name, input_type: type, type: ct ?? c.type }
              : c,
          ),
        );
        setUserInteracted(true);
      } else if (pickerTarget.kind === "custom") {
        setLabelSet((prev) =>
          prev.map((f) => (f.key === pickerTarget.key ? { ...f, label: name, type } : f)),
        );
        setUserInteracted(true);
      }
    },
    [pickerTarget],
  );

  const getFieldLabel = useCallback(
    (key: string, fallback: string): string => {
      const override = fieldLabels[key];
      return override && override.trim() ? override : fallback;
    },
    [fieldLabels],
  );

  useEffect(() => {
    if (!pendingLogoFile) {
      setPendingLogoPreview(null);
      return;
    }
    const url = URL.createObjectURL(pendingLogoFile);
    setPendingLogoPreview(url);
    return () => URL.revokeObjectURL(url);
  }, [pendingLogoFile]);

  const { data: card, isLoading: cardLoading } = useQuery({
    queryKey: ["card", id],
    queryFn: () => cardsApi.get(id!).then((r) => r.data),
    enabled: mode === "edit" && !!id,
  });

  const { data: cardMessages } = useQuery({
    queryKey: ["cardMessages", id],
    queryFn: () => cardMessagesApi.list(id!).then((r) => r.data),
    enabled: mode === "edit" && !!id && card?.is_active === false,
  });

  const activeMessage = cardMessages?.find((m) => !m.deleted_at) ?? null;
  const deleteMessageMutation = useMutation({
    mutationFn: (msgId: string) => cardMessagesApi.remove(id!, msgId),
    onSuccess: () => {
      toast.success("Сообщение удалено, карта восстановлена");
      void qc.invalidateQueries({ queryKey: ["cardMessages", id] });
      void qc.invalidateQueries({ queryKey: ["card", id] });
      void qc.invalidateQueries({ queryKey: ["cards"] });
    },
    onError: () => {
      toast.error("Не удалось удалить сообщение");
    },
  });

  const { data: templates } = useQuery({
    queryKey: ["templates"],
    queryFn: () => templatesApi.list().then((r) => r.data),
  });

  const form = useForm<CardFormData>({
    resolver: zodResolver(cardSchema),
    defaultValues: {
      last_name: "",
      first_name: "",
      middle_name: "",
      category_id: undefined,
      membership_no: "",
      birth_date: "",
      region: "",
      card_issue_date: "",
      join_date: "",
      chairman: "",
      bg_kind: "solid",
      bg_color: "#1F1E5E",
      bg_gradient_from: "",
      bg_gradient_to: "",
      bg_gradient_angle: 135,
      avatar_color: "",
      avatar_gradient_from: "",
      avatar_gradient_to: "",
      avatar_gradient_angle: 135,
      photo_shape: "square",
      hide_birth_date: false,
      hide_region: false,
      hide_card_issue_date: false,
      hide_join_date: false,
      hide_chairman: false,
      feedback_form_enabled: true,
      template_id: initialTemplateId ?? "",
    },
  });

  const watchedValues = useWatch({ control: form.control });

  useEffect(() => {
    if (mode !== "create" || !initialTemplateId || !templates) return;
    const tpl = templates.find((t) => t.id === initialTemplateId);
    if (!tpl) return;
    if (tpl.category_id) form.setValue("category_id", tpl.category_id);
    const styles = (tpl.default_styles ?? {}) as {
      bg_kind?: "solid" | "gradient";
      bg_color?: string;
      bg_gradient?: { start?: string; end?: string; from?: string; to?: string; angle?: number };
      photo_shape?: "square" | "circle";
    };
    if (styles.bg_kind) form.setValue("bg_kind", styles.bg_kind);
    if (styles.bg_color) form.setValue("bg_color", styles.bg_color);
    if (styles.bg_gradient) {
      form.setValue("bg_gradient_from", styles.bg_gradient.start ?? styles.bg_gradient.from ?? "#1F1E5E");
      form.setValue("bg_gradient_to", styles.bg_gradient.end ?? styles.bg_gradient.to ?? "#798BFF");
      if (styles.bg_gradient.angle) form.setValue("bg_gradient_angle", styles.bg_gradient.angle);
    }
    if (styles.photo_shape) {
      form.setValue("photo_shape", styles.photo_shape);
      setPhotoShape(styles.photo_shape);
    }
    const fields = (tpl.default_fields ?? {}) as Record<string, string>;
    if (fields.chairman) form.setValue("chairman", fields.chairman);
  }, [mode, initialTemplateId, templates, form]);

  useEffect(() => {
    if (card) {
      form.reset(
        {
          last_name: card.last_name,
          first_name: card.first_name,
          middle_name: card.middle_name ?? "",
          category_id: card.category_id,
          membership_no: card.membership_no,
          birth_date: card.birth_date ?? "",
          region: card.region ?? "",
          card_issue_date: card.card_issue_date ?? "",
          join_date: card.join_date ?? "",
          chairman: card.chairman ?? "",
          bg_kind: (card.bg_kind as "solid" | "gradient") ?? "solid",
          bg_color: card.bg_color ?? "#1F1E5E",
          bg_gradient_from: card.bg_gradient?.from ?? "",
          bg_gradient_to: card.bg_gradient?.to ?? "",
          bg_gradient_angle: card.bg_gradient?.angle ?? 135,
          avatar_color: card.avatar_color ?? "",
          avatar_gradient_from: card.avatar_gradient?.from ?? "",
          avatar_gradient_to: card.avatar_gradient?.to ?? "",
          avatar_gradient_angle: card.avatar_gradient?.angle ?? 135,
          photo_shape: (card.photo_shape as "square" | "circle") ?? "square",
          hide_birth_date: card.hide_birth_date ?? false,
          hide_region: card.hide_region ?? false,
          hide_card_issue_date: card.hide_card_issue_date ?? false,
          hide_join_date: card.hide_join_date ?? false,
          hide_chairman: card.hide_chairman ?? false,
          feedback_form_enabled: card.feedback_form_enabled,
          template_id: card.template_id ?? "",
        },
        { keepDefaultValues: false, keepDirty: false },
      );
      setSlugValue(card.public_slug);
      setPhotoKey(card.photo_key ?? null);
      setLogoKey(card.logo_key ?? null);
      setLogoShape((card.logo_shape as "square" | "circle" | "rectangle") ?? "square");
      setPhotoShape((card.photo_shape as "square" | "circle") ?? "square");
      setFieldOrder(
        Array.isArray(card.field_order) && card.field_order.length
          ? card.field_order
          : defaultFieldOrder(),
      );
      if (Array.isArray(card.label_set)) {
        setLabelSet(
          (card.label_set as CustomField[]).map((f, i) => ({
            ...f,
            key: f.key || genFieldKey() + `_${i}`,
          })),
        );
      }
      if (Array.isArray(card.contacts)) {
        setContacts(card.contacts as ContactBlock[]);
      }
      if (Array.isArray(card.internal_blocks)) {
        setInternalBlocks(card.internal_blocks as ContactBlock[]);
      }
      if (card.field_labels && typeof card.field_labels === "object") {
        setFieldLabels(card.field_labels as Record<string, string>);
      }
    }
  }, [card, form]);

  const createMutation = useMutation({
    mutationFn: (data: CardCreateRequest) => cardsApi.create(data),
    onSuccess: async (res) => {
      const newCardId = res.data.id;
      if (pendingPhotoFile) {
        try {
          const fd = new FormData();
          fd.append("file", pendingPhotoFile);
          await apiClient.post(`/cards/${newCardId}/photo`, fd, {
            headers: { "Content-Type": "multipart/form-data" },
          });
        } catch {
          toast.error("Карточка создана, но не удалось загрузить фото");
        }
      }
      if (pendingLogoFile) {
        try {
          const fd = new FormData();
          fd.append("file", pendingLogoFile);
          const r = await apiClient.post(`/cards/${newCardId}/logo`, fd, {
            headers: { "Content-Type": "multipart/form-data" },
          });
          setLogoKey(r.data.logo_key as string);
          setPendingLogoFile(null);
        } catch {
          toast.error("Карточка создана, но не удалось загрузить логотип");
        }
      }
      void qc.invalidateQueries({ queryKey: ["cards"] });
      acceptInteractionsAfter.current = Date.now() + 500;
      savingRef.current = true;
      form.reset(form.getValues());
      setUserInteracted(false);
      setPendingPayload(null);
      setPendingPhotoFile(null);
      setSuccessOpen(true);
      navigate(`/admin/cards/${newCardId}/edit`, { replace: true });
    },
    onError: (err: unknown) => {
      const apiErr = extractApiError(err);
      if (apiErr?.details?.field === "membership_no") {
        form.setError("membership_no", { type: "server", message: apiErr.message });
      }
      const fieldDetails = formatValidationErrors(apiErr);
      toast.error(apiErr?.message ?? "Ошибка при создании карточки", {
        description: fieldDetails ?? undefined,
        duration: fieldDetails ? 15000 : 5000,
      });
    },
  });

  const updateMutation = useMutation({
    mutationFn: (data: Partial<CardCreateRequest>) => cardsApi.update(id!, data),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ["cards"] });
      void qc.invalidateQueries({ queryKey: ["card", id] });
      acceptInteractionsAfter.current = Date.now() + 500;
      form.reset(form.getValues());
      setUserInteracted(false);
      setPendingPayload(null);
      setSuccessOpen(true);
    },
    onError: (err: unknown) => {
      const apiErr = extractApiError(err);
      if (apiErr?.details?.field === "membership_no") {
        form.setError("membership_no", { type: "server", message: apiErr.message });
      }
      const fieldDetails = formatValidationErrors(apiErr);
      toast.error(apiErr?.message ?? "Ошибка при сохранении", {
        description: fieldDetails ?? undefined,
        duration: fieldDetails ? 15000 : 5000,
      });
    },
  });

  const handleLogoChange = useCallback(
    (newKey: string | null) => {
      const prev = logoKey;
      setLogoKey(newKey);
      if (mode === "edit" && id) {
        cardsApi
          .update(id, { logo_key: newKey })
          .then(() => {
            void qc.invalidateQueries({ queryKey: ["card", id] });
            void qc.invalidateQueries({ queryKey: ["cards"] });
          })
          .catch(() => {
            setLogoKey(prev);
            toast.error("Не удалось обновить логотип");
          });
      }
    },
    [logoKey, mode, id, qc],
  );

  const handleLogoShapeChange = useCallback(
    (next: "square" | "circle" | "rectangle") => {
      const prev = logoShape;
      setLogoShape(next);
      setUserInteracted(true);
      if (mode === "edit" && id) {
        cardsApi
          .update(id, { logo_shape: next })
          .then(() => {
            void qc.invalidateQueries({ queryKey: ["card", id] });
          })
          .catch(() => {
            setLogoShape(prev);
            toast.error("Не удалось обновить форму логотипа");
          });
      }
    },
    [logoShape, mode, id, qc],
  );

  const [pendingPayload, setPendingPayload] = useState<CardCreateRequest | null>(null);
  const [criticalDiffs, setCriticalDiffs] = useState<DiffEntry[]>([]);
  const [successOpen, setSuccessOpen] = useState(false);
  const [slugModalOpen, setSlugModalOpen] = useState(false);
  const [pendingCreatePayload, setPendingCreatePayload] = useState<CardCreateRequest | null>(null);

  function buildPayload(data: CardFormData): CardCreateRequest {
    return {
      last_name: data.last_name,
      first_name: data.first_name,
      middle_name: data.middle_name || undefined,
      category_id: data.category_id ?? undefined,
      membership_no: data.membership_no,
      birth_date: data.birth_date || undefined,
      region: data.region || undefined,
      card_issue_date: data.card_issue_date || undefined,
      join_date: data.join_date || undefined,
      chairman: data.chairman || undefined,
      bg_kind: data.bg_kind,
      bg_color: data.bg_color || undefined,
      bg_gradient:
        data.bg_kind === "gradient" && data.bg_gradient_from && data.bg_gradient_to
          ? {
              from: data.bg_gradient_from,
              to: data.bg_gradient_to,
              angle: data.bg_gradient_angle ?? 135,
            }
          : undefined,
      avatar_color: data.avatar_color || null,
      avatar_gradient:
        data.avatar_gradient_from && data.avatar_gradient_to
          ? {
              from: data.avatar_gradient_from,
              to: data.avatar_gradient_to,
              angle: data.avatar_gradient_angle ?? 135,
            }
          : null,
      photo_shape: data.photo_shape,
      label_set: labelSet,
      internal_blocks: internalBlocks,
      hide_birth_date: data.hide_birth_date,
      hide_region: data.hide_region,
      hide_card_issue_date: data.hide_card_issue_date,
      hide_join_date: data.hide_join_date,
      hide_chairman: data.hide_chairman,
      feedback_form_enabled: data.feedback_form_enabled,
      contacts: contacts,
      template_id: data.template_id || undefined,
      logo_key: logoKey,
      logo_shape: logoShape,
      field_order: buildFieldRenderOrder(fieldOrder, labelSet).map((it) =>
        it.kind === "preset" ? it.key : it.field.key,
      ),
      field_labels: fieldLabels,
    };
  }

  function commitSave(payload: CardCreateRequest) {
    if (mode === "create") {
      createMutation.mutate(payload);
    } else {
      updateMutation.mutate(payload);
    }
  }

  function computeCriticalDiffs(data: CardFormData): DiffEntry[] {
    if (mode !== "edit" || !card) return [];
    const out: DiffEntry[] = [];
    if (data.last_name !== card.last_name) {
      out.push({ label: "Фамилия", before: card.last_name, after: data.last_name });
    }
    if (data.first_name !== card.first_name) {
      out.push({ label: "Имя", before: card.first_name, after: data.first_name });
    }
    if ((data.middle_name ?? "") !== (card.middle_name ?? "")) {
      out.push({
        label: "Отчество",
        before: card.middle_name ?? "",
        after: data.middle_name ?? "",
      });
    }
    if ((data.card_issue_date ?? "") !== (card.card_issue_date ?? "")) {
      out.push({
        label: "Дата выдачи билета",
        before: card.card_issue_date ?? "",
        after: data.card_issue_date ?? "",
      });
    }
    return out;
  }

  function onInvalid() {
    toast.error("Заполните обязательные поля — они отмечены красным");
    requestAnimationFrame(() => {
      document
        .querySelector('[aria-invalid="true"]')
        ?.scrollIntoView({ behavior: "smooth", block: "center" });
    });
  }

  function onSubmit(data: CardFormData) {
    const payload = buildPayload(data);
    const diffs = computeCriticalDiffs(data);
    if (diffs.length > 0) {
      setCriticalDiffs(diffs);
      setPendingPayload(payload);
      return;
    }
    if (mode === "create") {
      setPendingCreatePayload(payload);
      setSlugModalOpen(true);
      return;
    }
    commitSave(payload);
  }

  const handleSlugConfirm = useCallback(
    (slug: string) => {
      if (!pendingCreatePayload) return;
      const payload = { ...pendingCreatePayload, public_slug: slug };
      setSlugValue(slug);
      setSlugModalOpen(false);
      setPendingCreatePayload(null);
      commitSave(payload);
    },
    [pendingCreatePayload],
  );

  const [userInteracted, setUserInteracted] = useState(false);
  const acceptInteractionsAfter = useRef<number>(0);
  useEffect(() => {
    const sub = form.watch(() => {
      if (Date.now() < acceptInteractionsAfter.current) return;
      setUserInteracted(true);
    });
    return () => sub.unsubscribe();
  }, [form]);
  useEffect(() => {
    if (card) {
      setUserInteracted(false);
      acceptInteractionsAfter.current = Date.now() + 800;
    }
  }, [card]);
  useEffect(() => {
    if (mode === "create") {
      acceptInteractionsAfter.current = Date.now() + 500;
    }
  }, [mode]);
  useEffect(() => {
    if (mode === "create" && initialTemplateId && templates) {
      acceptInteractionsAfter.current = Date.now() + 400;
    }
  }, [mode, initialTemplateId, templates]);

  const savingRef = useRef(false);
  const isDirty = userInteracted || pendingPhotoFile !== null || pendingLogoFile !== null;
  const blocker = useDirtyFormBlocker(
    isDirty && !successOpen,
    () => savingRef.current,
  );

  const isSubmitting = createMutation.isPending || updateMutation.isPending;

  const bgPickerValue = {
    bg_kind: (watchedValues.bg_kind ?? "solid") as "solid" | "gradient",
    bg_color: watchedValues.bg_color,
    bg_gradient:
      watchedValues.bg_gradient_from && watchedValues.bg_gradient_to
        ? {
            from: watchedValues.bg_gradient_from,
            to: watchedValues.bg_gradient_to,
            angle: watchedValues.bg_gradient_angle ?? 135,
          }
        : undefined,
  };

  const avatarPickerValue: {
    bg_kind: "solid" | "gradient";
    bg_color?: string;
    bg_gradient?: { from: string; to: string; angle: number };
  } = {
    bg_kind: watchedValues.avatar_gradient_from && watchedValues.avatar_gradient_to ? "gradient" : "solid",
    bg_color: watchedValues.avatar_color || "#D6D6D6",
    bg_gradient:
      watchedValues.avatar_gradient_from && watchedValues.avatar_gradient_to
        ? {
            from: watchedValues.avatar_gradient_from,
            to: watchedValues.avatar_gradient_to,
            angle: watchedValues.avatar_gradient_angle ?? 135,
          }
        : undefined,
  };

  if (mode === "edit" && cardLoading) {
    return (
      <div className="space-y-4">
        <Skeleton className="h-8 w-64" />
        <Skeleton className="h-96 w-full" />
      </div>
    );
  }

  return (
    <div className="space-y-6 bg-white -mx-4 -my-4 px-4 py-4 md:-mx-6 md:-my-8 md:px-6 md:py-8 min-h-[calc(100vh-72px)]">
      <div className="flex items-center gap-3">
        <button
          type="button"
          onClick={() => navigate("/admin/cards")}
          aria-label="Назад"
          className="flex h-10 w-10 items-center justify-center rounded-full bg-white border-2 border-std-border hover:border-std-primary/40 transition-colors"
        >
          <ArrowLeft className="h-4 w-4 text-std-primary" />
        </button>
        <div className="flex-1">
          <h1 className="text-base font-semibold text-std-ink">
            {mode === "create" ? "Создать карточку" : "Редактировать карточку"}
          </h1>
        </div>
      </div>

      {mode === "edit" && card && card.is_active === false && (
        <div className="rounded-2xl border border-[#FECACA] bg-[#FEF2F2] px-4 py-3 text-sm text-[#991B1B] space-y-2">
          <p className="font-semibold">Удостоверение помечено недействительным</p>
          {activeMessage ? (
            <div className="rounded-xl bg-white border border-[#FECACA] p-3 space-y-2">
              {activeMessage.image_key && (
                <img
                  src={`/api/media/${activeMessage.image_key}`}
                  alt=""
                  className="w-full max-h-48 object-cover rounded-lg"
                />
              )}
              {activeMessage.text && (
                <p className="text-sm text-std-ink whitespace-pre-wrap">{activeMessage.text}</p>
              )}
              <button
                type="button"
                onClick={() => deleteMessageMutation.mutate(activeMessage.id)}
                disabled={deleteMessageMutation.isPending}
                className="inline-flex items-center gap-2 rounded-full bg-[#991B1B] text-white text-xs font-semibold px-4 py-2 hover:bg-[#7F1D1D] disabled:opacity-60"
              >
                {deleteMessageMutation.isPending ? "Удаляем…" : "Удалить сообщение и восстановить карту"}
              </button>
            </div>
          ) : (
            <p>Карта неактивна. Нет связанного сообщения.</p>
          )}
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-[minmax(0,1fr)_minmax(0,1fr)_380px] gap-4 items-start">
        <Form {...form}>
          <form
            id="card-edit-form"
            onSubmit={form.handleSubmit(onSubmit, onInvalid)}
            className="space-y-4 lg:col-span-2"
          >
            <div className="space-y-2 lg:grid lg:grid-cols-2 lg:gap-4 lg:items-start lg:space-y-0">
              <div className="space-y-4">

              {/* 1. Аватар — Figma 1:1: 200x200 white tile + 2 pill buttons */}
              <section className="bg-std-surface-2 border border-std-border rounded-3xl px-4 py-3">
                <h2 className="text-base font-semibold text-std-ink mb-3">Аватар</h2>
                <div className="flex flex-col items-center gap-5">
                  {(() => {
                    const url =
                      mode === "edit" && photoKey ? `/api/media/${photoKey}` : pendingPhotoPreview;
                    const last = (watchedValues.last_name ?? "").trim();
                    const first = (watchedValues.first_name ?? "").trim();
                    const initials = `${last[0] ?? "И"}${first[0] ?? "И"}`.toUpperCase();
                    const bgStyle: React.CSSProperties = {};
                    const c = watchedValues.avatar_color;
                    const gf = watchedValues.avatar_gradient_from;
                    const gt = watchedValues.avatar_gradient_to;
                    const ga = watchedValues.avatar_gradient_angle ?? 135;
                    if (gf && gt) bgStyle.background = `linear-gradient(${ga}deg, ${gf}, ${gt})`;
                    else if (c) bgStyle.background = c;
                    const tileClass = cn(
                      "flex items-center justify-center overflow-hidden border border-std-border bg-std-avatar-default h-[200px] w-[200px]",
                      photoShape === "circle" ? "rounded-full" : "rounded-3xl",
                    );
                    const inner = url ? (
                      <img src={url} alt="Аватар" className="h-full w-full object-cover" />
                    ) : (
                      <span
                        className="font-medium text-black"
                        style={{ fontSize: 85, lineHeight: 1, letterSpacing: "0.0235em" }}
                      >
                        {initials}
                      </span>
                    );
                    if (url) {
                      return (
                        <DropdownMenu>
                          <DropdownMenuTrigger asChild>
                            <button
                              type="button"
                              aria-label="Изменить фото"
                              className={cn(tileClass, "cursor-pointer focus:outline-none")}
                              style={bgStyle}
                            >
                              {inner}
                            </button>
                          </DropdownMenuTrigger>
                          <DropdownMenuContent align="center" className="w-48">
                            <DropdownMenuItem onClick={() => setPendingCropSrc(url)}>
                              Перекадрировать
                            </DropdownMenuItem>
                            <DropdownMenuItem
                              onClick={() =>
                                document.getElementById("pending-photo-input")?.click()
                              }
                            >
                              Заменить фото
                            </DropdownMenuItem>
                          </DropdownMenuContent>
                        </DropdownMenu>
                      );
                    }
                    return (
                      <div className={tileClass} style={bgStyle}>
                        {inner}
                      </div>
                    );
                  })()}

                  <input
                    id="pending-photo-input"
                    type="file"
                    accept="image/jpeg,image/png,image/webp"
                    className="hidden"
                    data-photo-input="true"
                    onChange={(e) => {
                      const file = e.target.files?.[0];
                      if (!file) return;
                      setPendingCropSrc(file);
                      e.target.value = "";
                    }}
                  />
                  {pendingCropSrc && (
                    <Suspense fallback={null}>
                      <AvatarCropDialog
                        src={pendingCropSrc}
                        cropShape={photoShape}
                        onConfirm={async (blob) => {
                          if (mode === "edit" && id) {
                            try {
                              const fd = new FormData();
                              fd.append("file", blob, "avatar.jpg");
                              const res = await apiClient.post(`/cards/${id}/photo`, fd, {
                                headers: { "Content-Type": "multipart/form-data" },
                              });
                              setPhotoKey(res.data.photo_key as string);
                              toast.success("Фото загружено");
                            } catch {
                              toast.error("Ошибка загрузки фото");
                            }
                          } else {
                            const cropped = new File([blob], "avatar.jpg", { type: "image/jpeg" });
                            setPendingPhotoFile(cropped);
                            if (pendingPhotoPreview) URL.revokeObjectURL(pendingPhotoPreview);
                            setPendingPhotoPreview(URL.createObjectURL(blob));
                          }
                          setPendingCropSrc(null);
                        }}
                        onCancel={() => setPendingCropSrc(null)}
                      />
                    </Suspense>
                  )}

                  <div className="flex w-full gap-2.5">
                    <Popover>
                      <PopoverTrigger asChild>
                        <button
                          type="button"
                          className="flex-1 h-10 rounded-full border border-std-border bg-white px-6 text-sm font-semibold text-std-primary hover:bg-std-surface-2 transition-colors"
                        >
                          Выбрать цвет
                        </button>
                      </PopoverTrigger>
                      <PopoverContent align="start" className="w-[320px] p-3">
                        <AvatarColorPicker
                          value={avatarPickerValue}
                          onChange={(next) => {
                            if (next.bg_kind === "gradient" && next.bg_gradient) {
                              form.setValue("avatar_gradient_from", next.bg_gradient.from);
                              form.setValue("avatar_gradient_to", next.bg_gradient.to);
                              form.setValue("avatar_gradient_angle", next.bg_gradient.angle);
                              form.setValue("avatar_color", "");
                            } else {
                              form.setValue("avatar_color", next.bg_color || "#D6D6D6");
                              form.setValue("avatar_gradient_from", "");
                              form.setValue("avatar_gradient_to", "");
                            }
                            setUserInteracted(true);
                          }}
                        />
                      </PopoverContent>
                    </Popover>
                    <button
                      type="button"
                      onClick={() => document.getElementById("pending-photo-input")?.click()}
                      className="flex-1 h-10 rounded-full bg-std-primary px-6 text-sm font-semibold text-white hover:bg-std-primary/90 transition-colors"
                    >
                      {mode === "edit" && photoKey ? "Изменить фото" : "Добавить фото"}
                    </button>
                  </div>
                </div>
              </section>

              {/* 2. Основная информация */}
              <section className="bg-std-surface-2 border border-std-border rounded-3xl px-4 py-3">
                <h2 className="text-base font-semibold text-std-ink mb-3">Основная информация</h2>
                <div className="space-y-3">
                  <LogoSelector
                    value={logoKey}
                    cardId={mode === "edit" ? id : undefined}
                    onChange={handleLogoChange}
                    shape={logoShape}
                    onShapeChange={handleLogoShapeChange}
                    pendingFile={pendingLogoFile}
                    onPendingFileChange={(file) => {
                      setPendingLogoFile(file);
                      setUserInteracted(true);
                    }}
                  />

                  <FormField
                    control={form.control}
                    name="membership_no"
                    render={({ field }) => (
                      <FormItem className="space-y-1.5">
                        <FormLabel asChild>
                          <button
                            type="button"
                            onClick={() => openPicker({ kind: "field", key: "membership_no" })}
                            className="text-sm font-semibold text-std-primary flex items-center gap-1 hover:opacity-80"
                          >
                            {getFieldLabel("membership_no", "№ Членского билета")}
                            <ChevronRight className="h-4 w-4" />
                          </button>
                        </FormLabel>
                        <FormControl>
                          <div className="relative rounded-xl bg-white px-4 py-3">
                            <Input
                              {...field}
                              placeholder="51467"
                              className="border-0 px-0 h-7 text-base shadow-none focus-visible:ring-0 pr-7"
                            />
                            {field.value && (
                              <button
                                type="button"
                                aria-label="Очистить"
                                onClick={() => field.onChange("")}
                                className="absolute right-4 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground"
                              >
                                <X className="h-4 w-4" />
                              </button>
                            )}
                          </div>
                        </FormControl>
                        <FormMessage />
                      </FormItem>
                    )}
                  />

                  <FioInput control={form.control} />

                </div>
              </section>

              {/* 5. Форма обратной связи */}
              <section className="bg-std-surface-2 border border-std-border rounded-3xl px-4 py-3">
                <h2 className="text-base font-semibold text-std-ink mb-3">Форма обратной связи с СТД</h2>
                <div className="space-y-3">
                  <ContactBlocksEditor
                    value={contacts}
                    onChange={setContacts}
                    onLabelClick={(idx) => openPicker({ kind: "contact", idx })}
                  />
                </div>
              </section>

              {/* 6. Служебная информация (Figma node 118:22811 — 3px periwinkle border) */}
              <section className="bg-std-surface-2 border-[3px] border-std-secondary rounded-3xl px-4 py-3">
                <h2 className="text-base font-semibold text-std-ink mb-3">Служебная информация</h2>
                <div className="space-y-3">
                  <ContactBlocksEditor
                    value={internalBlocks}
                    onChange={setInternalBlocks}
                    addButtonLabel="Добавить поле"
                    onLabelClick={(idx) => openPicker({ kind: "internal", idx })}
                  />
                </div>
              </section>

            </div>

            <div className="space-y-4">
              {/* col2.1 — Форма аватара (Figma: stacked above Цвет фона) */}
              <section className="bg-std-surface-2 border border-std-border rounded-3xl px-4 py-3">
                  <h2 className="text-base font-semibold text-std-ink mb-3">Форма аватара</h2>
                  <Tabs
                    value={photoShape}
                    onValueChange={(value) => {
                      const shape = value as "square" | "circle";
                      setPhotoShape(shape);
                      form.setValue("photo_shape", shape);
                    }}
                  >
                    <TabsList className="flex gap-4 h-auto bg-transparent p-0 rounded-none">
                      <TabsTrigger
                        value="square"
                        aria-label="Квадратная форма аватара"
                        className="h-20 w-20 p-0 rounded-2xl bg-white border border-std-border transition-colors data-[state=active]:border-2 data-[state=active]:border-std-primary data-[state=active]:shadow-none data-[state=active]:bg-white"
                      />
                      <TabsTrigger
                        value="circle"
                        aria-label="Круглая форма аватара"
                        className="h-20 w-20 p-0 rounded-full bg-white border border-std-border transition-colors data-[state=active]:border-2 data-[state=active]:border-std-primary data-[state=active]:shadow-none data-[state=active]:bg-white"
                      />
                    </TabsList>
                  </Tabs>
                </section>

              {/* col2.2 — Цвет фона карточки */}
              <section data-accordion-value="bg" className="bg-std-surface-2 border border-std-border rounded-3xl px-4 py-3">
                <h2 className="text-base font-semibold text-std-ink mb-3">Цвет фона карточки</h2>
                  <div className="space-y-2.5">
                    <Tabs
                      value={watchedValues.bg_kind ?? "solid"}
                      onValueChange={(value) => {
                        form.setValue("bg_kind", value as "solid" | "gradient");
                        setUserInteracted(true);
                      }}
                      className="w-full"
                    >
                      <TabsList className="inline-flex w-full h-auto rounded-full bg-std-surface-3 p-1">
                        <TabsTrigger
                          value="solid"
                          className="flex-1 rounded-full px-4 py-1.5 text-sm font-semibold transition-colors text-std-muted-fg hover:text-black data-[state=active]:bg-white data-[state=active]:text-std-primary data-[state=active]:shadow-sm"
                        >
                          Монохром
                        </TabsTrigger>
                        <TabsTrigger
                          value="gradient"
                          className="flex-1 rounded-full px-4 py-1.5 text-sm font-semibold transition-colors text-std-muted-fg hover:text-black data-[state=active]:bg-white data-[state=active]:text-std-primary data-[state=active]:shadow-sm"
                        >
                          Градиент
                        </TabsTrigger>
                      </TabsList>
                    </Tabs>
                    <BackgroundPicker
                      compact
                      value={bgPickerValue}
                      onChange={(next) => {
                        form.setValue("bg_kind", next.bg_kind);
                        if (next.bg_color) form.setValue("bg_color", next.bg_color);
                        if (next.bg_gradient) {
                          form.setValue("bg_gradient_from", next.bg_gradient.from);
                          form.setValue("bg_gradient_to", next.bg_gradient.to);
                          form.setValue("bg_gradient_angle", next.bg_gradient.angle);
                        }
                      }}
                    />
                  </div>
                </section>

              {/* col2.3 — Дополнительная информация (preset rows + custom + Председатель) */}
              <section className="bg-std-surface-2 border border-std-border rounded-3xl px-4 py-3">
                <h2 className="text-base font-semibold text-std-ink mb-3">Дополнительная информация</h2>
                <div className="space-y-3">
                  <DndContext
                    sensors={dndSensors}
                    collisionDetection={closestCenter}
                    onDragEnd={handleFieldOrderDragEnd}
                  >
                    <SortableContext items={editorIds} strategy={verticalListSortingStrategy}>
                      <div className="divide-y divide-std-border/60 [&>*]:py-3 first:[&>*]:pt-0 last:[&>*]:pb-0">
                        {editorFields.map((it) => {
                          if (it.kind === "custom") {
                            const cf = it.field;
                            return (
                              <SortableCustomFieldRow
                                key={cf.key}
                                id={cf.key}
                                field={cf}
                                onUpdate={(patch) => updateCustomField(cf.key, patch)}
                                onRemove={() => removeCustomField(cf.key)}
                                onLabelClick={() => openPicker({ kind: "custom", key: cf.key })}
                              />
                            );
                          }
                          const key = it.key;
                          if (key === "birth_date") {
                            return (
                              <SortablePresetRow
                                key={key}
                                id={key}
                                label={getFieldLabel("birth_date", "Дата рождения")}
                                hidden={watchedValues.hide_birth_date ?? false}
                                onLabelClick={() => openPicker({ kind: "field", key: "birth_date" })}
                              >
                                <FormField
                                  control={form.control}
                                  name="birth_date"
                                  render={({ field }) => (
                                    <FormItem>
                                      <FormControl>
                                        <DatePickerField
                                          value={field.value ?? ""}
                                          onChange={field.onChange}
                                        />
                                      </FormControl>
                                      <FormMessage />
                                    </FormItem>
                                  )}
                                />
                              </SortablePresetRow>
                            );
                          }
                          if (key === "region") {
                            return (
                              <SortablePresetRow
                                key={key}
                                id={key}
                                label={getFieldLabel("region", "Регион")}
                                hidden={watchedValues.hide_region ?? false}
                                onLabelClick={() => openPicker({ kind: "field", key: "region" })}
                              >
                                <FormField
                                  control={form.control}
                                  name="region"
                                  render={({ field }) => (
                                    <FormItem>
                                      <FormControl>
                                        <RegionAutocomplete
                                          value={field.value}
                                          onChange={field.onChange}
                                        />
                                      </FormControl>
                                      <FormMessage />
                                    </FormItem>
                                  )}
                                />
                              </SortablePresetRow>
                            );
                          }
                          if (key === "card_issue_date") {
                            return (
                              <SortablePresetRow
                                key={key}
                                id={key}
                                label={getFieldLabel("card_issue_date", "Дата выдачи билета")}
                                hidden={watchedValues.hide_card_issue_date ?? false}
                                onLabelClick={() => openPicker({ kind: "field", key: "card_issue_date" })}
                              >
                                <FormField
                                  control={form.control}
                                  name="card_issue_date"
                                  render={({ field }) => (
                                    <FormItem>
                                      <FormControl>
                                        <DatePickerField
                                          value={field.value ?? ""}
                                          onChange={field.onChange}
                                        />
                                      </FormControl>
                                      <FormMessage />
                                    </FormItem>
                                  )}
                                />
                              </SortablePresetRow>
                            );
                          }
                          if (key === "join_date") {
                            return (
                              <SortablePresetRow
                                key={key}
                                id={key}
                                label={getFieldLabel("join_date", "Член СТД с")}
                                hidden={watchedValues.hide_join_date ?? false}
                                onLabelClick={() => openPicker({ kind: "field", key: "join_date" })}
                              >
                                <FormField
                                  control={form.control}
                                  name="join_date"
                                  render={({ field }) => (
                                    <FormItem>
                                      <FormControl>
                                        <DatePickerField
                                          value={field.value ?? ""}
                                          onChange={field.onChange}
                                          yearOnly
                                        />
                                      </FormControl>
                                      <FormMessage />
                                    </FormItem>
                                  )}
                                />
                              </SortablePresetRow>
                            );
                          }
                          return null;
                        })}
                      </div>
                    </SortableContext>
                  </DndContext>

                  <div className="h-px bg-std-border my-3" />
                  <button
                    type="button"
                    onClick={addCustomField}
                    className="flex h-12 w-full items-center justify-start gap-2 rounded-xl border border-std-border bg-white px-5 text-sm font-semibold text-std-primary transition-colors hover:bg-std-surface-2"
                  >
                    <Plus className="h-5 w-5" />
                    Добавить поле
                  </button>
                </div>
              </section>

              {/* col2.4 — Председатель (gray card, same style as other sections) */}
              <section className="bg-std-surface-2 border border-std-border rounded-3xl px-4 py-3">
                <FormField
                  control={form.control}
                  name="chairman"
                  render={({ field }) => (
                    <FormItem className="space-y-1.5">
                      <FormLabel asChild>
                        <button
                          type="button"
                          onClick={() => openPicker({ kind: "field", key: "chairman" })}
                          className="text-sm font-semibold text-std-primary flex items-center gap-1 whitespace-normal text-left hover:opacity-80"
                        >
                          {getFieldLabel(
                            "chairman",
                            "Председатель союза театральных деятелей Российской Федерации",
                          )}
                          <ChevronRight className="h-4 w-4 shrink-0" />
                        </button>
                      </FormLabel>
                      <FormControl>
                        <div className="relative rounded-xl bg-white px-4 py-3">
                          <Input
                            {...field}
                            placeholder="Иванов И.И."
                            className="border-0 px-0 h-7 text-base shadow-none focus-visible:ring-0 pr-7"
                          />
                          {field.value && (
                            <button
                              type="button"
                              aria-label="Очистить"
                              onClick={() => field.onChange("")}
                              className="absolute right-4 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground"
                            >
                              <X className="h-4 w-4" />
                            </button>
                          )}
                        </div>
                      </FormControl>
                      <FormMessage />
                    </FormItem>
                  )}
                />
              </section>
            </div>
            </div>

            <div className="pt-2 flex sm:flex-row gap-2 lg:hidden">
              <Button
                type="submit"
                disabled={isSubmitting}
                className="w-full sm:w-auto rounded-full bg-std-primary hover:bg-std-primary/90"
              >
                {isSubmitting ? (
                  <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                ) : null}
                Сохранить
                {!isSubmitting && <Check className="h-4 w-4 ml-2" />}
              </Button>
            </div>
          </form>
        </Form>

        <div className="hidden lg:block lg:sticky lg:top-4">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-base font-semibold text-std-ink">Предпросмотр</h2>
            <Button
              type="submit"
              form="card-edit-form"
              disabled={isSubmitting}
              className="h-10 rounded-full bg-std-primary hover:bg-std-primary/90 px-6"
            >
              {isSubmitting && <Loader2 className="h-4 w-4 mr-2 animate-spin" />}
              Сохранить
              {!isSubmitting && <Check className="h-4 w-4 ml-2" />}
            </Button>
          </div>
          <MemberCardPreview
            pendingLogoUrl={pendingLogoPreview}
            pendingPhotoUrl={pendingPhotoPreview}
            payload={{
              photo_key: photoKey,
              last_name: watchedValues.last_name ?? "",
              first_name: watchedValues.first_name ?? "",
              middle_name: watchedValues.middle_name || undefined,
              membership_no: watchedValues.membership_no || "",
              birth_date: watchedValues.birth_date || undefined,
              region: watchedValues.region || undefined,
              card_issue_date: watchedValues.card_issue_date || undefined,
              join_date: watchedValues.join_date || undefined,
              chairman: watchedValues.chairman || undefined,
              bg_kind: watchedValues.bg_kind ?? "solid",
              bg_color: watchedValues.bg_color || undefined,
              bg_gradient:
                watchedValues.bg_kind === "gradient" &&
                watchedValues.bg_gradient_from &&
                watchedValues.bg_gradient_to
                  ? {
                      from: watchedValues.bg_gradient_from,
                      to: watchedValues.bg_gradient_to,
                      angle: watchedValues.bg_gradient_angle ?? 135,
                    }
                  : undefined,
              avatar_color: watchedValues.avatar_color || null,
              avatar_gradient:
                watchedValues.avatar_gradient_from && watchedValues.avatar_gradient_to
                  ? {
                      from: watchedValues.avatar_gradient_from,
                      to: watchedValues.avatar_gradient_to,
                      angle: watchedValues.avatar_gradient_angle ?? 135,
                    }
                  : null,
              photo_shape: photoShape,
              logo_shape: logoShape,
              logo_key: logoKey,
              label_set: labelSet,
              field_order: fieldOrder,
              field_labels: fieldLabels,
              contacts: contacts,
              internal_blocks: internalBlocks,
              hide_birth_date: watchedValues.hide_birth_date ?? false,
              hide_region: watchedValues.hide_region ?? false,
              hide_card_issue_date: watchedValues.hide_card_issue_date ?? false,
              hide_join_date: watchedValues.hide_join_date ?? false,
              hide_chairman: watchedValues.hide_chairman ?? false,
              feedback_form_enabled: watchedValues.feedback_form_enabled ?? true,
            }}
          />
        </div>
      </div>

      <QuitConfirmModal
        open={blocker.open}
        onProceed={blocker.proceed}
        onCancel={blocker.cancel}
      />

      <ApproveSaveModal
        open={pendingPayload !== null}
        diffs={criticalDiffs}
        isPending={createMutation.isPending || updateMutation.isPending}
        onConfirm={() => {
          if (pendingPayload) commitSave(pendingPayload);
        }}
        onCancel={() => {
          setPendingPayload(null);
          setCriticalDiffs([]);
        }}
      />

      <SaveSuccessModal
        open={successOpen}
        title={mode === "create" ? "Карточка создана!" : "Карточка сохранена!"}
        onClose={() => setSuccessOpen(false)}
      />

      <SlugCreateModal
        open={slugModalOpen}
        onClose={() => {
          setSlugModalOpen(false);
          setPendingCreatePayload(null);
        }}
        onConfirm={handleSlugConfirm}
        submitting={createMutation.isPending}
      />

      <LabelPickerSheet
        open={pickerTarget !== null}
        onClose={() => setPickerTarget(null)}
        onApply={applyPickedLabel}
      />
    </div>
  );
}
