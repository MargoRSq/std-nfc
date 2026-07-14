import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { apiClient } from "./client";

export type LabelPresetType = "text" | "number" | "date" | "url" | "phone" | "email";

export const LABEL_PRESET_TYPE_OPTIONS: { value: LabelPresetType; label: string }[] = [
  { value: "text", label: "Текст" },
  { value: "number", label: "Число" },
  { value: "date", label: "Дата" },
  { value: "url", label: "Ссылка" },
  { value: "phone", label: "Телефон" },
  { value: "email", label: "Email" },
];

export interface LabelPreset {
  id: string;
  admin_id: string;
  name: string;
  type: LabelPresetType;
  order_idx: number;
  created_at: string;
  updated_at: string;
}

export interface SystemLabelPreset {
  id: string;
  name: string;
  type: LabelPresetType;
  is_system: true;
}

export const SYSTEM_LABEL_PRESETS: SystemLabelPreset[] = [
  { id: "system:birth_date", name: "Дата рождения", type: "date", is_system: true },
  { id: "system:region", name: "Регион", type: "text", is_system: true },
  { id: "system:card_issue_date", name: "Дата выдачи билета", type: "date", is_system: true },
  { id: "system:join_date", name: "Член СТД с", type: "date", is_system: true },
  {
    id: "system:chairman",
    name: "Председатель союза театральных деятелей Российской Федерации",
    type: "text",
    is_system: true,
  },
  { id: "system:phone", name: "Телефон", type: "phone", is_system: true },
  { id: "system:email", name: "Email", type: "email", is_system: true },
  { id: "system:website", name: "Сайт", type: "url", is_system: true },
  { id: "system:telegram", name: "Telegram", type: "text", is_system: true },
  { id: "system:whatsapp", name: "WhatsApp", type: "phone", is_system: true },
  { id: "system:max", name: "MAX", type: "text", is_system: true },
  { id: "system:vk", name: "ВКонтакте", type: "url", is_system: true },
  { id: "system:ok", name: "Одноклассники", type: "url", is_system: true },
  { id: "system:instagram", name: "Instagram", type: "text", is_system: true },
  { id: "system:youtube", name: "YouTube", type: "url", is_system: true },
  { id: "system:tiktok", name: "TikTok", type: "text", is_system: true },
];

export const labelPresetsApi = {
  list: () => apiClient.get<LabelPreset[]>("/label-presets/"),
  create: (name: string, type: LabelPresetType = "text") =>
    apiClient.post<LabelPreset>("/label-presets/", { name, type }),
  update: (id: string, name: string, type: LabelPresetType) =>
    apiClient.patch<LabelPreset>(`/label-presets/${id}`, { name, type }),
  delete: (id: string) => apiClient.delete(`/label-presets/${id}`),
  reorder: (ids: string[]) =>
    apiClient.post("/label-presets/reorder", { ids }),
};

const QK = ["label-presets"] as const;

export function useLabelPresets() {
  return useQuery({
    queryKey: QK,
    queryFn: () => labelPresetsApi.list().then((r) => r.data),
    staleTime: 60_000,
  });
}

export function useCreateLabelPreset() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ name, type }: { name: string; type: LabelPresetType }) =>
      labelPresetsApi.create(name, type).then((r) => r.data),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: QK });
    },
  });
}

export function useUpdateLabelPreset() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, name, type }: { id: string; name: string; type: LabelPresetType }) =>
      labelPresetsApi.update(id, name, type).then((r) => r.data),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: QK });
    },
  });
}

export function useDeleteLabelPreset() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => labelPresetsApi.delete(id),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: QK });
    },
  });
}
