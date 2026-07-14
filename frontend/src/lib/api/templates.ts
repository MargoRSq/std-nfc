import { apiClient } from "./client";

export interface Template {
  id: string;
  name: string;
  category_id?: number | null;
  default_fields: Record<string, unknown>;
  default_styles: Record<string, unknown>;
  custom_field_schema?: Record<string, unknown>[];
  is_default?: boolean;
  created_at: string;
}

export type TemplateDeleteCascade = "template_only" | "with_cards";

export interface TemplateDeleteResult {
  cards_deleted: number;
  cards_reassigned: number;
}

export interface TemplateCreateRequest {
  name: string;
  category_id: number;
  default_fields?: Record<string, unknown>;
  default_styles?: Record<string, unknown>;
  custom_field_schema?: Record<string, unknown>[];
}

export const templatesApi = {
  list: () => apiClient.get<Template[]>("/templates/"),
  get: (id: string) => apiClient.get<Template>(`/templates/${id}`),
  create: (data: TemplateCreateRequest) => apiClient.post<Template>("/templates/", data),
  update: (id: string, data: Partial<TemplateCreateRequest>) =>
    apiClient.patch<Template>(`/templates/${id}`, data),
  delete: (id: string, cascade: TemplateDeleteCascade = "template_only") =>
    apiClient.delete<TemplateDeleteResult>(`/templates/${id}`, { params: { cascade } }),
  createFromCard: (cardId: string, name: string) =>
    apiClient.post<Template>(`/templates/from-card/${cardId}`, { name }),
};
